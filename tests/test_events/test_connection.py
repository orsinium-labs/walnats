from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import pytest

import walnats

from ..helpers import get_random_name


if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


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


async def test_emit_sync(event: walnats.Event, caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger='walnats')
    assert not caplog.records
    events = walnats.Events(event)
    async with events.connect() as con:
        await con.register()

        await con.emit(event, '', uid='m1')
        assert not caplog.records

        await con.emit(event, '', uid='m1')
        assert not caplog.records

        await con.emit(event, '', uid='m1', sync=True)
        assert len(caplog.records) == 1
        r = caplog.records[0]
        assert r.levelname == 'DEBUG'
        assert r.message == 'duplicate message'

        await con.emit(event, '', uid='m2', sync=True)
        assert len(caplog.records) == 1


@pytest.mark.parametrize('create', [True, False])
@pytest.mark.parametrize('update', [True, False])
async def test_register__twice_same_event(create, update):
    name = get_random_name()
    event = walnats.Event(name, str)
    events = walnats.Events(event)
    async with events.connect() as conn:
        await conn.register()
        await conn.register(create=create, update=update)


@pytest.mark.parametrize('kwargs, raises', [
    (dict(create=False, update=False), None),
    (dict(create=True, update=False), walnats.StreamExistsError),
    (dict(create=False, update=True), None),
    (dict(create=True, update=True), None),
])
async def test_register__twice_can_update(kwargs, raises: type[Exception]):
    name = get_random_name()
    event = walnats.Event(name, str, limits=walnats.Limits(age=60))
    events = walnats.Events(event)
    async with events.connect() as conn:
        await conn.register()

    event = walnats.Event(name, str, limits=walnats.Limits(age=30))
    events = walnats.Events(event)
    async with events.connect() as conn:
        if raises is None:
            await conn.register(**kwargs)
        else:
            with pytest.raises(raises):
                await conn.register(**kwargs)


@pytest.mark.parametrize('kwargs, raises', [
    (dict(create=False, update=False), None),
    (dict(create=True, update=False), walnats.StreamExistsError),
    (dict(create=False, update=True), walnats.StreamConfigError),
    (dict(create=True, update=True), walnats.StreamConfigError),
])
async def test_register__twice_cannot_update(kwargs, raises: type[Exception]):
    name = get_random_name()
    event = walnats.Event(name, str, limits=walnats.Limits(consumers=10))
    events = walnats.Events(event)
    async with events.connect() as conn:
        await conn.register()

    event = walnats.Event(name, str, limits=walnats.Limits(consumers=20))
    events = walnats.Events(event)
    async with events.connect() as conn:
        if raises is None:
            await conn.register(**kwargs)
        else:
            with pytest.raises(raises):
                await conn.register(**kwargs)


async def test_register__invalid_name():
    event = walnats.Event('hello*world', str)  # noqa: WNS003
    events = walnats.Events(event)
    async with events.connect() as conn:
        with pytest.raises(walnats.StreamConfigError):
            await conn.register()


async def test_register__negative_limit():
    event = walnats.Event(
        get_random_name(), str,
        limits=walnats.Limits(age=-10),  # noqa: WNS011
    )
    events = walnats.Events(event)
    async with events.connect() as conn:
        with pytest.raises(walnats.StreamConfigError):
            await conn.register()
