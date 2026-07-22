"""Tolerant structural extraction for MQL5 compilation units."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from .diagnostics import Diagnostic, UNMATCHED_DELIMITER
from .graph import SourceLocation
from .lexer import Token, tokenize


EVENT_HANDLERS = {
    "OnStart", "OnInit", "OnDeinit", "OnTick", "OnCalculate", "OnTimer", "OnTrade",
    "OnTradeTransaction", "OnBookEvent", "OnChartEvent", "OnTester", "OnTesterInit",
    "OnTesterPass", "OnTesterDeinit",
}

_CONTROL_WORDS = {"if", "for", "while", "switch", "return", "sizeof", "catch", "else"}
_POST_SIGNATURE = {"const", "override", "final", "virtual", "inline"}


@dataclass(frozen=True, slots=True)
class IncludeRef:
    target: str
    system: bool
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class Declaration:
    kind: str
    name: str
    qualified_name: str
    signature: str
    location: SourceLocation
    body_start: int | None = None
    body_end: int | None = None
    parameter_count: int | None = None


@dataclass(frozen=True, slots=True)
class CallSite:
    caller: str
    name: str
    qualifier: str | None
    argument_count: int
    location: SourceLocation


@dataclass(slots=True)
class ParseResult:
    file: str
    includes: list[IncludeRef] = field(default_factory=list)
    declarations: list[Declaration] = field(default_factory=list)
    calls: list[CallSite] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def _pairs(tokens: list[Token], opening: str, closing: str, file: str) -> tuple[dict[int, int], list[Diagnostic]]:
    stack: list[int] = []
    pairs: dict[int, int] = {}
    diagnostics: list[Diagnostic] = []
    for index, token in enumerate(tokens):
        if token.value == opening:
            stack.append(index)
        elif token.value == closing:
            if stack:
                start = stack.pop()
                pairs[start] = index
            else:
                diagnostics.append(Diagnostic(
                    UNMATCHED_DELIMITER, "warning", f"Unmatched {closing}",
                    SourceLocation(file, token.line, token.column),
                ))
    for index in stack:
        token = tokens[index]
        diagnostics.append(Diagnostic(
            UNMATCHED_DELIMITER, "warning", f"Unmatched {opening}",
            SourceLocation(file, token.line, token.column),
        ))
    return pairs, diagnostics


def _join_signature(tokens: list[Token]) -> str:
    result = ""
    for token in tokens:
        if result and token.value not in {",", ")", "]", ";"} and result[-1] not in "([:.&*":
            result += " "
        result += token.value
    return result.strip()


def _argument_count(tokens: list[Token], start: int, end: int) -> int:
    if end <= start + 1:
        return 0
    depth = 0
    count = 1
    has_value = False
    for token in tokens[start + 1:end]:
        if token.value in {"(", "[", "{"}:
            depth += 1
        elif token.value in {")", "]", "}"}:
            depth = max(0, depth - 1)
        elif token.value == "," and depth == 0:
            count += 1
        elif token.value not in {"const", "&"}:
            has_value = True
    return count if has_value else 0


def parse_source(text: str, file: str) -> ParseResult:
    lexed = tokenize(text, file)
    tokens = lexed.tokens[:-1]
    result = ParseResult(file=file, diagnostics=list(lexed.diagnostics))
    parens, diagnostics = _pairs(tokens, "(", ")", file)
    braces, brace_diagnostics = _pairs(tokens, "{", "}", file)
    result.diagnostics.extend(diagnostics)
    result.diagnostics.extend(brace_diagnostics)

    include_pattern = re.compile(r"^\s*#\s*include\s*([<\"])([^>\"]+)[>\"]")
    for token in tokens:
        if token.kind != "preprocessor":
            continue
        match = include_pattern.match(token.value)
        if match:
            result.includes.append(IncludeRef(
                target=match.group(2).strip(), system=match.group(1) == "<",
                location=SourceLocation(file, token.line, token.column),
            ))

    type_ranges: list[tuple[int, int, str, str]] = []
    for index, token in enumerate(tokens[:-2]):
        if token.value not in {"class", "struct", "enum"} or tokens[index + 1].kind != "identifier":
            continue
        name_token = tokens[index + 1]
        open_index = next((cursor for cursor in range(index + 2, min(len(tokens), index + 20))
                           if tokens[cursor].value in {"{", ";"}), None)
        if open_index is None:
            continue
        body_end = braces.get(open_index) if tokens[open_index].value == "{" else None
        declaration = Declaration(
            kind=token.value, name=name_token.value, qualified_name=name_token.value,
            signature=name_token.value,
            location=SourceLocation(file, name_token.line, name_token.column),
            body_start=open_index if body_end is not None else None, body_end=body_end,
        )
        result.declarations.append(declaration)
        if body_end is not None:
            type_ranges.append((open_index, body_end, name_token.value, token.value))

    depth_at: list[int] = []
    depth = 0
    for token in tokens:
        depth_at.append(depth)
        if token.value == "{":
            depth += 1
        elif token.value == "}":
            depth = max(0, depth - 1)

    functions: list[Declaration] = []
    for open_paren, close_paren in sorted(parens.items()):
        if open_paren == 0:
            continue
        name_index = open_paren - 1
        name_token = tokens[name_index]
        if name_token.kind != "identifier" or name_token.value in _CONTROL_WORDS:
            continue
        owner = next((item for item in type_ranges if item[0] < open_paren < item[1]), None)
        expected_depth = 1 if owner else 0
        if depth_at[open_paren] != expected_depth:
            continue
        cursor = close_paren + 1
        while cursor < len(tokens) and tokens[cursor].value in _POST_SIGNATURE:
            cursor += 1
        if cursor >= len(tokens) or tokens[cursor].value not in {"{", ";"}:
            continue
        if name_index > 0 and tokens[name_index - 1].value in {".", "->"}:
            continue

        boundary = name_index - 1
        while boundary >= 0 and tokens[boundary].value not in {";", "{", "}"}:
            boundary -= 1
        prefix = tokens[boundary + 1:name_index]
        if not prefix and name_token.value not in {owner[2] if owner else ""}:
            continue
        owner_name = owner[2] if owner else None
        qualified_name = f"{owner_name}::{name_token.value}" if owner_name else name_token.value
        kind = "event_handler" if name_token.value in EVENT_HANDLERS and not owner else ("method" if owner else "function")
        body_start = cursor if tokens[cursor].value == "{" else None
        body_end = braces.get(cursor) if body_start is not None else None
        signature = f"{qualified_name}({_join_signature(tokens[open_paren + 1:close_paren])})"
        declaration = Declaration(
            kind=kind, name=name_token.value, qualified_name=qualified_name, signature=signature,
            location=SourceLocation(file, name_token.line, name_token.column),
            body_start=body_start, body_end=body_end,
            parameter_count=_argument_count(tokens, open_paren, close_paren),
        )
        functions.append(declaration)
        result.declarations.append(declaration)

    for function in functions:
        if function.body_start is None:
            continue
        end = function.body_end if function.body_end is not None else len(tokens)
        cursor = function.body_start + 1
        while cursor < end - 1:
            token = tokens[cursor]
            if token.kind == "identifier" and tokens[cursor + 1].value == "(" and token.value not in _CONTROL_WORDS:
                close = parens.get(cursor + 1)
                if close is not None and close <= end:
                    qualifier = None
                    if cursor >= 2 and tokens[cursor - 1].value in {".", "->", "::"}:
                        qualifier = tokens[cursor - 2].value
                    result.calls.append(CallSite(
                        caller=function.qualified_name, name=token.value, qualifier=qualifier,
                        argument_count=_argument_count(tokens, cursor + 1, close),
                        location=SourceLocation(file, token.line, token.column),
                    ))
                    cursor += 1
            cursor += 1

    result.declarations.sort(key=lambda item: (item.location.line, item.location.column, item.qualified_name))
    result.calls.sort(key=lambda item: (item.location.line, item.location.column, item.name))
    return result
