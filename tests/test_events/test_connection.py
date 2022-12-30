from __future__ import annotations

import asyncio
from typing import Any

import pytest
from ..helpers import get_random_name

import walnats


async def test_events_monitor(event: walnats.Event):
    events = walnats.Events(event)
    async with events.connect() as conn:
        with conn.monitor() as monitor:
            asyncio.create_task(conn.emit(event, 'hello'))
            recv = await asyncio.wait_for(monitor.get(), timeout=2)
            assert recv == 'hello'


@pytest.mark.parametrize('given, expected', [
    (
        dict(),
        None,
    ),
    (
        dict(meta={'hello': 'world'}),
        {'hello': 'world'},
    ),
    (
        dict(meta={'hello': 'world'}, uid='oh-hi-mark'),
        {'hello': 'world', 'Nats-Msg-Id': 'oh-hi-mark'},
    ),
    (
        dict(uid='test-me'),
        {'Nats-Msg-Id': 'test-me'},
    ),
    (
        dict(uid='check-mate', trace_id='some-number'),
        {'Nats-Msg-Id': 'check-mate', 'Walnats-Trace': 'some-number'},
    ),
    (
        dict(meta=walnats.CloudEvent(id='id1', source='src1', type='type1')),
        {
            'Nats-Msg-Id': 'id1',
            'ce-id': 'id1',
            'ce-source': 'src1',
            'ce-specversion': '1.0',
            'ce-type': 'type1',
        },
    ),
    (
        dict(meta=walnats.CloudEvent(id='id1', source='src1', type='type1'), uid='uid1'),
        {
            'Nats-Msg-Id': 'uid1',
            'ce-id': 'id1',
            'ce-source': 'src1',
            'ce-specversion': '1.0',
            'ce-type': 'type1',
        },
    ),

])
async def test_headers(
    given: dict[str, Any],
    expected: dict[str, str],
    event: walnats.Event,
) -> None:

    headers: dict | None = None

    class MW(walnats.middlewares.Middleware):
        def on_start(self, ctx: walnats.types.Context) -> None:
            nonlocal headers
            headers = ctx._msg.headers

    actor = walnats.Actor(get_random_name(), event, lambda _: None, middlewares=(MW(),))

    actors = walnats.Actors(actor)
    events = walnats.Events(event)
    async with events.connect() as econ, actors.connect() as acon:
        await econ.register()
        await acon.register()
        await econ.emit(event, 'hi', **given)
        await acon.listen(burst=True)
    assert headers == expected
