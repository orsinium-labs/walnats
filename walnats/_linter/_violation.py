from __future__ import annotations

import ast
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Violation:
    node: ast.AST
    code: int

    @property
    def message(self) -> str:
        return MESSAGES[self.code]


MESSAGES = MappingProxyType({
    1: 'event name is empty',
    2: 'event name is too long',
    3: 'event name has invalid symbols',
    4: 'event name should use kebab-case',

    10: 'must be a positive number',
    11: 'age must be in seconds',
})
