from __future__ import annotations

from tableau2pbip.calc.ast import (
    Binary,
    Call,
    Case,
    Conditional,
    Expr,
    Field,
    Literal,
    Lod,
    ParameterRef,
    Unary,
)
from tableau2pbip.calc.lexer import Token, lex


class ParseError(ValueError):
    pass


_BINDING_POWER = {
    "OR": 10,
    "AND": 20,
    "=": 30,
    "<>": 30,
    "!=": 30,
    "<": 30,
    ">": 30,
    "<=": 30,
    ">=": 30,
    "+": 40,
    "-": 40,
    "*": 50,
    "/": 50,
    "^": 60,
}


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        token = self.current
        self.index += 1
        return token

    def match(self, kind: str, value: str | None = None) -> bool:
        if self.current.kind != kind:
            return False
        return value is None or self.current.value.casefold() == value.casefold()

    def expect(self, kind: str, value: str | None = None) -> Token:
        if not self.match(kind, value):
            expected = value if value is not None else kind
            raise ParseError(
                f"Expected {expected!r} at position {self.current.position}, "
                f"found {self.current.value!r}"
            )
        return self.advance()

    def match_word(self, *values: str) -> bool:
        return self.current.kind == "IDENT" and self.current.value.upper() in values

    def expect_word(self, value: str) -> Token:
        if not self.match_word(value):
            raise ParseError(
                f"Expected {value} at position {self.current.position}, "
                f"found {self.current.value!r}"
            )
        return self.advance()

    def parse(self) -> Expr:
        result = self.expression()
        if self.current.kind != "EOF":
            raise ParseError(
                f"Unexpected token {self.current.value!r} at position {self.current.position}"
            )
        return result

    def expression(self, minimum: int = 0, stops: frozenset[str] = frozenset()) -> Expr:
        if self.current.kind == "IDENT" and self.current.value.upper() in stops:
            raise ParseError(
                f"Expected expression before {self.current.value} at {self.current.position}"
            )
        left = self.prefix()
        while self.current.kind != "EOF":
            if self.current.kind == "IDENT" and self.current.value.upper() in stops:
                break
            operator = self.current.value.upper() if self.current.kind == "IDENT" else self.current.value
            binding = _BINDING_POWER.get(operator)
            if binding is None or binding < minimum:
                break
            self.advance()
            right = self.expression(binding + 1, stops)
            left = Binary(operator, left, right)
        return left

    def prefix(self) -> Expr:
        token = self.advance()
        if token.kind in {"NUMBER", "STRING", "DATE"}:
            return Literal(token.value, token.kind.lower())
        if token.kind == "FIELD":
            if self.match("DOT"):
                self.advance()
                field = self.expect("FIELD").value
                if token.value.casefold() == "parameters":
                    return ParameterRef(field)
                return Field(f"{token.value}.{field}")
            return Field(token.value)
        if token.kind == "OP" and token.value in {"+", "-"}:
            return Unary(token.value, self.expression(55))
        if token.kind == "LPAREN":
            nested = self.expression()
            self.expect("RPAREN")
            return nested
        if token.kind == "LBRACE":
            return self.lod()
        if token.kind == "IDENT":
            word = token.value.upper()
            if word == "NOT":
                return Unary("NOT", self.expression(25))
            if word == "IF":
                return self.conditional()
            if word == "CASE":
                return self.case()
            if word in {"TRUE", "FALSE"}:
                return Literal(word.lower(), "bool")
            if word in {"NULL", "BLANK"}:
                return Literal("", "blank")
            if self.match("LPAREN"):
                return self.call(token.value)
            return Field(token.value)
        raise ParseError(f"Unexpected token {token.value!r} at position {token.position}")

    def call(self, name: str) -> Expr:
        self.expect("LPAREN")
        arguments: list[Expr] = []
        if not self.match("RPAREN"):
            while True:
                arguments.append(self.expression())
                if not self.match("COMMA"):
                    break
                self.advance()
        self.expect("RPAREN")
        return Call(name.upper(), arguments)

    def conditional(self) -> Expr:
        condition = self.expression(stops=frozenset({"THEN"}))
        self.expect_word("THEN")
        branches: list[tuple[Expr, Expr]] = []
        result = self.expression(stops=frozenset({"ELSEIF", "ELSE", "END"}))
        branches.append((condition, result))
        while self.match_word("ELSEIF"):
            self.advance()
            next_condition = self.expression(stops=frozenset({"THEN"}))
            self.expect_word("THEN")
            next_result = self.expression(stops=frozenset({"ELSEIF", "ELSE", "END"}))
            branches.append((next_condition, next_result))
        otherwise: Expr | None = None
        if self.match_word("ELSE"):
            self.advance()
            otherwise = self.expression(stops=frozenset({"END"}))
        self.expect_word("END")
        return Conditional(branches, otherwise)

    def case(self) -> Expr:
        value = self.expression(stops=frozenset({"WHEN"}))
        branches: list[tuple[Expr, Expr]] = []
        while self.match_word("WHEN"):
            self.advance()
            match_value = self.expression(stops=frozenset({"THEN"}))
            self.expect_word("THEN")
            result = self.expression(stops=frozenset({"WHEN", "ELSE", "END"}))
            branches.append((match_value, result))
        otherwise: Expr | None = None
        if self.match_word("ELSE"):
            self.advance()
            otherwise = self.expression(stops=frozenset({"END"}))
        self.expect_word("END")
        return Case(value, branches, otherwise)

    def lod(self) -> Expr:
        kind = "table"
        dimensions: list[str] = []
        if self.match_word("FIXED"):
            self.advance()
            kind = "fixed"
            while True:
                dimensions.append(self.expect("FIELD").value)
                if not self.match("COMMA"):
                    break
                self.advance()
            self.expect("COLON")
        expression = self.expression(stops=frozenset())
        self.expect("RBRACE")
        return Lod(kind, dimensions, expression)


def parse(source: str) -> Expr:
    return _Parser(lex(source)).parse()
