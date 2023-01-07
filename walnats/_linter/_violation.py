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
    5: 'event description is empty',
    6: 'event description is too long',

    11: 'limit must be positive',
    12: 'age must be in seconds',

    21: 'actor name is empty',
    22: 'actor name is too long',
    23: 'actor name has invalid symbols',
    24: 'actor name should use kebab-case',
    25: 'actor description is empty',
    26: 'actor description is too long',
})
