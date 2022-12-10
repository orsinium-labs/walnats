from __future__ import annotations

import asyncio

import walnats

from .helpers import get_random_name


def test_events_get():
    events = walnats.Events(
        walnats.Event('e1', str),
        walnats.Event('e2', str),
        walnats.Event('e3', str),
    )
    e1 = events.get('e1')
    assert e1
    assert e1.name == 'e1'
    e2 = events.get('e2')
    assert e2
    assert e2.name == 'e2'
    assert events.get('something') is None


async def test_events_monitor():
    event = walnats.Event(get_random_name(), str)
    events = walnats.Events(event)
    async with events.connect() as conn:
        with conn.monitor() as monitor:
            asyncio.create_task(conn.emit(event, 'hello'))
            recv = await asyncio.wait_for(monitor.get(), timeout=2)
            assert recv == 'hello'
