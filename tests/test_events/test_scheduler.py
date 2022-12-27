from __future__ import annotations

import asyncio
from datetime import datetime

import walnats

from ..helpers import get_random_name


async def test_scheduler() -> None:
    received = []

    def handler(event) -> None:
        received.append(event)

    e = walnats.Event(get_random_name(), datetime)
    s = walnats.Scheduler(e, period=1)
    a = walnats.Actor(get_random_name(), e, handler)
    events_reg = walnats.Events(e)
    actors_reg = walnats.Actors(a)

    async with events_reg.connect() as pub_conn, actors_reg.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await s.run(pub_conn, burst=True)
        await asyncio.sleep(.01)
        await sub_conn.listen(burst=True)
    assert len(received) == 1
