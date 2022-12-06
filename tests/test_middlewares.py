from __future__ import annotations

import asyncio
from collections import Counter
import logging
from typing import TYPE_CHECKING, Callable

import pytest

import walnats

from .helpers import get_random_name


if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


class MockMiddleware(walnats.middlewares.Middleware):
    def __init__(self) -> None:
        self.hist: list[str] = []

    def on_start(self, ctx) -> None:
        self.hist.append('on_start')

    def on_success(self, ctx) -> None:
        self.hist.append('on_success')

    def on_failure(self, ctx) -> None:
        self.hist.append('on_failure')


async def run_actor(
    handler: Callable,
    messages: str | list[str],
    *middlewares: walnats.middlewares.Middleware,
    **kwargs,
) -> None:
    event = walnats.Event(get_random_name(), str)
    actor = walnats.Actor(get_random_name(), event, handler, middlewares=middlewares)
    events_reg = walnats.Events(actor.event)
    actors_reg = walnats.Actors(actor)
    if isinstance(messages, str):
        messages = [messages]
    async with events_reg.connect() as pub_conn, actors_reg.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await asyncio.gather(*[pub_conn.emit(event, m) for m in messages])
        if len(messages) > 1:
            await asyncio.sleep(.01)
        await sub_conn.listen(burst=True, batch=len(messages), **kwargs)


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
async def test_ExtraLogMiddleware(caplog: LogCaptureFixture) -> None:
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
async def test_ExtraLogMiddleware__on_failure(caplog: LogCaptureFixture) -> None:
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


@pytest.mark.asyncio
async def test_ErrorThresholdMiddleware(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)

    async def handler(msg: str) -> None:
        1/0

    mw = MockMiddleware()
    await run_actor(handler, 'hi', walnats.middlewares.ErrorThresholdMiddleware(mw))
    assert mw.hist == ['on_start']

    mw = MockMiddleware()
    await run_actor(
        handler,
        ['hi'] * 40,
        walnats.middlewares.ErrorThresholdMiddleware(mw),
    )
    assert Counter(mw.hist) == Counter(dict(on_start=40, on_failure=19))


@pytest.mark.asyncio
async def test_FrequencyMiddleware(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    switch = False

    async def handler(msg: str) -> None:
        nonlocal switch
        switch = not switch
        if switch:
            1/0

    mw = MockMiddleware()
    await run_actor(
        handler,
        ['hi'] * 40,
        walnats.middlewares.FrequencyMiddleware(mw),
    )
    assert Counter(mw.hist) == Counter(dict(on_success=1, on_failure=1, on_start=1))
