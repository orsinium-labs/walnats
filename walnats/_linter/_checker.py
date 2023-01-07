from __future__ import annotations

import ast
from typing import Iterator

from ._finders import get_violations


TEMPLATE = 'WNS0{code:02} {message}'


class Flake8Checker:
    name = 'walnats'
    version = '0.0.1'
    _tree: ast.AST

    def __init__(
        self,
        tree: ast.AST,
        file_tokens=None,
        filename=None,
    ) -> None:
        self._tree = tree

    def run(self) -> Iterator[tuple]:
        for v in get_violations(self._tree):
            text = TEMPLATE.format(code=v.code, message=v.message)
            yield v.node.lineno, v.node.col_offset, text, type(self)
