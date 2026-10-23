from __future__ import annotations

from dataclasses import dataclass


class LexError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    value: str
    position: int


def lex(source: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    length = len(source)
    while index < length:
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if source.startswith("//", index):
            newline = source.find("\n", index)
            index = length if newline < 0 else newline + 1
            continue
        if char == "[":
            end = source.find("]", index + 1)
            if end < 0:
                raise LexError(f"Unclosed field reference at position {index}")
            tokens.append(Token("FIELD", source[index + 1 : end], index))
            index = end + 1
            continue
        if char == "#":
            end = source.find("#", index + 1)
            if end < 0:
                raise LexError(f"Unclosed date literal at position {index}")
            tokens.append(Token("DATE", source[index + 1 : end], index))
            index = end + 1
            continue
        if char in {"'", '"'}:
            quote = char
            start = index
            index += 1
            value: list[str] = []
            while index < length:
                current = source[index]
                if current == quote:
                    if index + 1 < length and source[index + 1] == quote:
                        value.append(quote)
                        index += 2
                        continue
                    index += 1
                    break
                value.append(current)
                index += 1
            else:
                raise LexError(f"Unclosed string literal at position {start}")
            tokens.append(Token("STRING", "".join(value), start))
            continue
        if char.isdigit() or (char == "." and index + 1 < length and source[index + 1].isdigit()):
            start = index
            index += 1
            while index < length and (source[index].isdigit() or source[index] == "."):
                index += 1
            if index < length and source[index] in "eE":
                index += 1
                if index < length and source[index] in "+-":
                    index += 1
                while index < length and source[index].isdigit():
                    index += 1
            tokens.append(Token("NUMBER", source[start:index], start))
            continue
        if char.isalpha() or char == "_":
            start = index
            index += 1
            while index < length and (source[index].isalnum() or source[index] in "_$"):
                index += 1
            tokens.append(Token("IDENT", source[start:index], start))
            continue
        two_char = source[index : index + 2]
        if two_char in {"<=", ">=", "<>", "!="}:
            tokens.append(Token("OP", two_char, index))
            index += 2
            continue
        punctuation = {
            "(": "LPAREN",
            ")": "RPAREN",
            ",": "COMMA",
            ":": "COLON",
            "{": "LBRACE",
            "}": "RBRACE",
            ".": "DOT",
        }
        if char in punctuation:
            tokens.append(Token(punctuation[char], char, index))
            index += 1
            continue
        if char in "+-*/^=<>":
            tokens.append(Token("OP", char, index))
            index += 1
            continue
        raise LexError(f"Unsupported character {char!r} at position {index}")
    tokens.append(Token("EOF", "", length))
    return tokens
