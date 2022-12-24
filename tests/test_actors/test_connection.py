from __future__ import annotations

import nats

import walnats

from ..helpers import get_random_name


async def test_actors_dont_own_connection():
    nc = await nats.connect()

    e = walnats.Event(get_random_name(), str)
    events = walnats.Events(e)
    async with events.connect(nc, close=False) as econn:
        await econn.register()
    assert not nc.is_closed

    a = walnats.Actor(get_random_name(), e, lambda _: None)
    actors = walnats.Actors(a)
    async with actors.connect(nc, close=False) as aconn:
        await aconn.register()
    assert not nc.is_closed
