from __future__ import annotations

import ast
import re
from typing import Iterator

from ._violation import Violation


REX_KEBAB = re.compile('[a-z0-9-]*')


def get_violations(tree: ast.AST) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _get_class_name(node.func)
            if name == 'Event':
                yield from _check_event(node)
            if name == 'Actor':
                yield from _check_actor(node)
            if name == 'Limits':
                yield from _check_limits(node)


def _check_event(node: ast.Call) -> Iterator[Violation]:
    name_node = _get_arg(node, 0, 'name')
    if isinstance(name_node, ast.Constant) and isinstance(name_node.value, str):
        name = name_node.value
        if not name:
            yield Violation(name_node, 1)
        if len(name) > 64:  # nats allows more, but let's keep it sane
            yield Violation(name_node, 2)
        if set(name) & set(' \t\r\n\f.*>'):
            yield Violation(name_node, 3)
        elif not REX_KEBAB.fullmatch(name):
            yield Violation(name_node, 4)

    descr_node = _get_arg(node, 3, 'description')
    if isinstance(descr_node, ast.Constant) and isinstance(descr_node.value, str):
        descr = descr_node.value
        if not descr:
            yield Violation(descr_node, 5)
        if len(descr) > 4 * 1024:
            yield Violation(descr_node, 6)


def _check_limits(node: ast.Call) -> Iterator[Violation]:
    names = ('age', 'consumers', 'messages', 'bytes', 'message_size')
    for index, name in enumerate(names):
        arg_node = _get_arg(node, index, name)
        if isinstance(arg_node, ast.UnaryOp):  # negative number, supposedly
            yield Violation(arg_node, 11)

    age_node = _get_arg(node, 0, 'age')
    if isinstance(age_node, ast.Constant) and isinstance(age_node.value, (float, int)):
        if age_node.value >= 1e9:
            yield Violation(age_node, 12)


def _check_actor(node: ast.Call) -> Iterator[Violation]:
    name_node = _get_arg(node, 0, 'name')
    if isinstance(name_node, ast.Constant) and isinstance(name_node.value, str):
        name = name_node.value
        if not name:
            yield Violation(name_node, 21)
        if len(name) > 64:  # nats allows more, but let's keep it sane
            yield Violation(name_node, 22)
        if set(name) & set(' \t\r\n\f.*>'):
            yield Violation(name_node, 23)
        elif not REX_KEBAB.fullmatch(name):
            yield Violation(name_node, 24)

    descr_node = _get_arg(node, 3, 'description')
    if isinstance(descr_node, ast.Constant) and isinstance(descr_node.value, str):
        descr = descr_node.value
        if not descr:
            yield Violation(descr_node, 25)
        if len(descr) > 4 * 1024:
            yield Violation(descr_node, 26)


def _get_class_name(node: ast.expr) -> str | None:
    if not isinstance(node, ast.Attribute):
        return None
    if not isinstance(node.value, ast.Name):
        return None
    if node.value.id != 'walnats':
        return None
    return node.attr


def _get_arg(node: ast.Call, index: int, name: str) -> ast.expr | None:
    try:
        return node.args[index]
    except IndexError:
        pass
    for kw in node.keywords:
        if kw.arg == name:
            return kw.value
    return None
