from __future__ import annotations

import asyncio

import walnats

from ..helpers import get_random_name


async def test_events_monitor():
    event = walnats.Event(get_random_name(), str)
    events = walnats.Events(event)
    async with events.connect() as conn:
        with conn.monitor() as monitor:
            asyncio.create_task(conn.emit(event, 'hello'))
            recv = await asyncio.wait_for(monitor.get(), timeout=2)
            assert recv == 'hello'
