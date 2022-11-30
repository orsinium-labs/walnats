from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable

import pytest

import walnats

from .helpers import get_random_name

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


async def run_actor(
    handler: Callable,
    message: str,
    *middlewares: walnats.middlewares.Middleware,
    **kwargs,
) -> None:
    event = walnats.Event(get_random_name(), str)
    actor = walnats.Actor(get_random_name(), event, handler, middlewares=middlewares)
    events_reg = walnats.Events(actor.event)
    actors_reg = walnats.Actors(actor)
    async with events_reg.connect() as pub_conn, actors_reg.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await asyncio.gather(
            sub_conn.listen(burst=True, **kwargs),
            pub_conn.emit(event, message),
        )


@pytest.mark.asyncio
async def test_custom_sync() -> None:
    triggered = []

    class Middleware(walnats.middlewares.Middleware):
        def on_failure(self, ctx: walnats.types.ErrorContext) -> None:
            triggered.append('on_failure')

        def on_start(self, ctx: walnats.types.Context) -> None:
            triggered.append('on_start')

        def on_success(self, ctx: walnats.types.OkContext) -> None:
            triggered.append('on_success')

    async def handler(msg: str) -> None:
        assert msg == 'hi'
        triggered.append('handler')

    await run_actor(handler, 'hi', Middleware())
    assert triggered == ['on_start', 'handler', 'on_success']


@pytest.mark.asyncio
async def test_custom_sync__on_failure() -> None:
    triggered = []

    class Middleware(walnats.middlewares.Middleware):
        def on_failure(self, ctx: walnats.types.ErrorContext) -> None:
            triggered.append('on_failure')

        def on_start(self, ctx: walnats.types.Context) -> None:
            triggered.append('on_start')

        def on_success(self, ctx: walnats.types.OkContext) -> None:
            triggered.append('on_success')

    async def handler(msg: str) -> None:
        assert msg == 'hi'
        triggered.append('handler')
        raise ZeroDivisionError

    await run_actor(handler, 'hi', Middleware())
    assert triggered == ['on_start', 'handler', 'on_failure']


@pytest.mark.asyncio
async def test_custom_async() -> None:
    triggered = []

    class Middleware(walnats.middlewares.Middleware):
        async def on_failure(self, ctx: walnats.types.ErrorContext) -> None:
            triggered.append('on_failure')
            raise ctx.exception

        async def on_start(self, ctx: walnats.types.Context) -> None:
            triggered.append('on_start')

        async def on_success(self, ctx: walnats.types.OkContext) -> None:
            triggered.append('on_success')

    async def handler(msg: str) -> None:
        assert msg == 'hi'
        triggered.append('handler')

    await run_actor(handler, 'hi', Middleware())
    assert len(triggered) == 3
    assert set(triggered) == {'on_start', 'handler', 'on_success'}


@pytest.mark.asyncio
async def test_custom_async__on_failure() -> None:
    triggered = []

    class Middleware(walnats.middlewares.Middleware):
        async def on_failure(self, ctx: walnats.types.ErrorContext) -> None:
            triggered.append('on_failure')

        async def on_start(self, ctx: walnats.types.Context) -> None:
            triggered.append('on_start')

        async def on_success(self, ctx: walnats.types.OkContext) -> None:
            triggered.append('on_success')

    async def handler(msg: str) -> None:
        assert msg == 'hi'
        triggered.append('handler')
        raise ZeroDivisionError

    await run_actor(handler, 'hi', Middleware())
    assert len(triggered) == 3
    assert set(triggered) == {'on_start', 'handler', 'on_failure'}


@pytest.mark.asyncio
async def test_extra_log_middleware(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)

    async def handler(msg: str) -> None:
        pass

    await run_actor(handler, 'hi', walnats.middlewares.ExtraLogMiddleware())
    records = []
    for record in caplog.records:
        if record.name.startswith('walnats'):
            records.append(record)
    assert len(records) == 2
    assert records[0].message == 'event received'
    assert records[1].message == 'event processed'


@pytest.mark.asyncio
async def test_extra_log_middleware__on_failure(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)

    async def handler(msg: str) -> None:
        1/0

    await run_actor(handler, 'hi', walnats.middlewares.ExtraLogMiddleware())
    records = []
    for record in caplog.records:
        if record.name.startswith('walnats'):
            records.append(record)
    assert len(records) == 3
    assert records[0].message == 'event received'
    assert records[1].message.startswith('Unhandled ZeroDivisionError in')
    assert records[2].message == 'actor failed'
