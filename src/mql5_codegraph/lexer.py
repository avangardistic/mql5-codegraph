"""A recovery-oriented MQL5 tokenizer with precise source coordinates."""

from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import Diagnostic, UNTERMINATED_COMMENT, UNTERMINATED_STRING
from .graph import SourceLocation


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    value: str
    line: int
    column: int
    offset: int


@dataclass(slots=True)
class LexResult:
    tokens: list[Token]
    diagnostics: list[Diagnostic]


_MULTI_OPERATORS = (
    "<<=", ">>=", "::", "->", "++", "--", "==", "!=", "<=", ">=", "&&", "||",
    "+=", "-=", "*=", "/=", "%=", "<<", ">>", "&=", "|=", "^=",
)


def tokenize(text: str, file: str) -> LexResult:
    tokens: list[Token] = []
    diagnostics: list[Diagnostic] = []
    index = 0
    line = 1
    column = 1
    length = len(text)

    def advance(value: str) -> None:
        nonlocal line, column
        newlines = value.count("\n")
        if newlines:
            line += newlines
            column = len(value.rsplit("\n", 1)[-1]) + 1
        else:
            column += len(value)

    while index < length:
        char = text[index]
        if char.isspace():
            start = index
            while index < length and text[index].isspace():
                index += 1
            advance(text[start:index])
            continue

        start_line, start_column, start_offset = line, column, index
        at_line_start = index == 0 or text[index - 1] == "\n" or text[text.rfind("\n", 0, index) + 1:index].strip() == ""
        if char == "#" and at_line_start:
            end = text.find("\n", index)
            if end == -1:
                end = length
            value = text[index:end]
            tokens.append(Token("preprocessor", value, line, column, index))
            index = end
            advance(value)
            continue

        if text.startswith("//", index):
            end = text.find("\n", index)
            if end == -1:
                end = length
            advance(text[index:end])
            index = end
            continue

        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end == -1:
                value = text[index:]
                diagnostics.append(Diagnostic(
                    UNTERMINATED_COMMENT, "warning", "Unterminated block comment",
                    SourceLocation(file, start_line, start_column),
                ))
                advance(value)
                index = length
            else:
                end += 2
                value = text[index:end]
                advance(value)
                index = end
            continue

        if char in {'"', "'"}:
            quote = char
            index += 1
            escaped = False
            while index < length:
                current = text[index]
                index += 1
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    break
                elif current == "\n":
                    break
            value = text[start_offset:index]
            if not value.endswith(quote):
                diagnostics.append(Diagnostic(
                    UNTERMINATED_STRING, "warning", "Unterminated string or character literal",
                    SourceLocation(file, start_line, start_column),
                ))
            tokens.append(Token("string", value, start_line, start_column, start_offset))
            advance(value)
            continue

        if char == "_" or char.isalpha():
            index += 1
            while index < length and (text[index] == "_" or text[index].isalnum()):
                index += 1
            value = text[start_offset:index]
            tokens.append(Token("identifier", value, line, column, start_offset))
            advance(value)
            continue

        if char.isdigit() or (char == "." and index + 1 < length and text[index + 1].isdigit()):
            index += 1
            while index < length and (text[index].isalnum() or text[index] in "._+-"):
                if text[index] in "+-" and text[index - 1] not in "eE":
                    break
                index += 1
            value = text[start_offset:index]
            tokens.append(Token("number", value, line, column, start_offset))
            advance(value)
            continue

        operator = next((item for item in _MULTI_OPERATORS if text.startswith(item, index)), None)
        value = operator or char
        tokens.append(Token("symbol", value, line, column, index))
        index += len(value)
        advance(value)

    tokens.append(Token("eof", "", line, column, length))
    return LexResult(tokens, diagnostics)
