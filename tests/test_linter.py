from __future__ import annotations

import ast

import pytest

from walnats._linter import Flake8Checker


@pytest.mark.parametrize('given, expected', [
    # skip invalid nodes, mypy should take care of it
    ('walnats', None),
    ('walnats.Garbage', None),
    ('walnats.Garbage()', None),
    ('walnats.Garbage("")', None),
    ('walnats.Event()', None),
    ('walnats().Event("")', None),
    ('nats.Event("")', None),
    ('Event("")', None),
    ('walnats.Event(garbage="")', None),

    # validate name
    ('walnats.Event("")', 'WNS001 event name is empty'),
    ('walnats.Event(name="")', 'WNS001 event name is empty'),
    ('walnats.Event("' + 'a' * 80 + '")', 'WNS002 event name is too long'),
    ('walnats.Event("hi there")', 'WNS003 event name has invalid symbols'),
    ('walnats.Event("Hi")', 'WNS004 event name should use kebab-case'),

    ('walnats.Limits(12)', None),
    ('walnats.Limits(age=12)', None),
    ('walnats.Limits(-12)', 'WNS010 must be a positive number'),
    ('walnats.Limits(age=-12)', 'WNS010 must be a positive number'),
    ('walnats.Limits(age=1e9)', 'WNS011 age must be in seconds'),
    ('walnats.Limits(age=1e10)', 'WNS011 age must be in seconds'),
    ('walnats.Limits(age=10000000000)', 'WNS011 age must be in seconds'),

])
def test_linter(given: str, expected: str | list | None):
    tree = ast.parse(given)
    print(ast.dump(tree))
    checker = Flake8Checker(tree)
    violations = list(checker.run())
    messages = [v[2] for v in violations]
    if expected is None:
        assert len(messages) == 0
    else:
        if isinstance(expected, str):
            expected = [expected]
        assert messages == expected
