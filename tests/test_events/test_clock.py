from __future__ import annotations

import asyncio
from datetime import datetime

import walnats

from ..helpers import get_random_name


async def test_clock() -> None:
    received = []

    def handler(event) -> None:
        received.append(event)

    event = walnats.Event(get_random_name(), datetime)
    clock = walnats.Clock(event, period=1)
    actor = walnats.Actor(get_random_name(), event, handler)
    events_reg = walnats.Events(event)
    actors_reg = walnats.Actors(actor)

    async with events_reg.connect() as pub_conn, actors_reg.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await clock.run(pub_conn, burst=True)
        await asyncio.sleep(.01)
        await sub_conn.listen(burst=True)
    assert len(received) == 1
