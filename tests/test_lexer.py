from unittest import TestCase

from mql5_codegraph.lexer import tokenize


class LexerTests(TestCase):
    def test_comments_and_string_contents_do_not_create_identifiers(self) -> None:
        result = tokenize('// GhostCall()\nPrint("HiddenCall()");', "sample.mq5")
        identifiers = [token.value for token in result.tokens if token.kind == "identifier"]
        self.assertEqual(["Print"], identifiers)

    def test_preprocessor_is_preserved_as_one_token(self) -> None:
        result = tokenize('#include "Risk.mqh"\nvoid OnTick() {}', "sample.mq5")
        self.assertEqual("preprocessor", result.tokens[0].kind)
        self.assertIn("Risk.mqh", result.tokens[0].value)

    def test_preprocessor_after_long_leading_whitespace_remains_linear_and_valid(self) -> None:
        result = tokenize(
            f'{" " * 100_000}#include "Risk.mqh"\nvalue # other',
            "sample.mq5",
        )

        self.assertEqual("preprocessor", result.tokens[0].kind)
        self.assertEqual("#", next(
            token.value for token in result.tokens
            if token.kind == "symbol"
        ))
