from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Literal:
    value: str
    kind: str


@dataclass(frozen=True, slots=True)
class Field:
    name: str


@dataclass(frozen=True, slots=True)
class ParameterRef:
    name: str


@dataclass(frozen=True, slots=True)
class Unary:
    operator: str
    operand: Expr


@dataclass(frozen=True, slots=True)
class Binary:
    operator: str
    left: Expr
    right: Expr


@dataclass(frozen=True, slots=True)
class Call:
    name: str
    arguments: list[Expr]


@dataclass(frozen=True, slots=True)
class Conditional:
    branches: list[tuple[Expr, Expr]]
    otherwise: Expr | None


@dataclass(frozen=True, slots=True)
class Case:
    value: Expr
    branches: list[tuple[Expr, Expr]]
    otherwise: Expr | None


@dataclass(frozen=True, slots=True)
class Lod:
    kind: str
    dimensions: list[str]
    expression: Expr


Expr = Literal | Field | ParameterRef | Unary | Binary | Call | Conditional | Case | Lod
