from __future__ import annotations

import walnats

from ..helpers import get_random_name


def test_actors_get():
    async def noop(_):
        pass

    e = walnats.Event(get_random_name(), str)
    actors = walnats.Actors(
        walnats.Actor('a1', e, noop),
        walnats.Actor('a2', e, noop),
        walnats.Actor('a3', e, noop),
    )
    a1 = actors.get('a1')
    assert a1
    assert a1.name == 'a1'
    a2 = actors.get('a2')
    assert a2
    assert a2.name == 'a2'
    assert actors.get('something') is None


def test_actors_iter():
    async def noop(_):
        pass

    e = walnats.Event(get_random_name(), str)
    a1 = walnats.Actor('a1', e, noop)
    a2 = walnats.Actor('a3', e, noop)
    a3 = walnats.Actor('a2', e, noop)
    actors = walnats.Actors(a1, a2, a3)
    assert list(actors) == [a1, a2, a3]
