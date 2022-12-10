from __future__ import annotations

import asyncio
from collections import Counter
import logging
import os
from typing import TYPE_CHECKING, Callable

import pytest
import sentry_sdk

import walnats

from .helpers import get_random_name, UDPLogProtocol, fuzzy_match_counter


if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


async def noop(msg: str) -> None:
    pass


async def explode(msg: str) -> None:
    1/0

SENTRY_DSN = os.environ.get('SENTRY_DSN')


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
    await run_actor(noop, 'hi', walnats.middlewares.ExtraLogMiddleware())
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
    await run_actor(explode, 'hi', walnats.middlewares.ExtraLogMiddleware())
    records = []
    for record in caplog.records:
        if record.name.startswith('walnats'):
            records.append(record)
    assert len(records) == 3
    assert records[0].message == 'event received'
    assert records[1].message.startswith('Unhandled ZeroDivisionError in')
    assert records[2].message == 'actor failed'


@pytest.mark.asyncio
async def test_ErrorThresholdMiddleware() -> None:
    mw = MockMiddleware()
    await run_actor(explode, 'hi', walnats.middlewares.ErrorThresholdMiddleware(mw))
    assert mw.hist == ['on_start']

    mw = MockMiddleware()
    await run_actor(
        explode, ['hi'] * 40,
        walnats.middlewares.ErrorThresholdMiddleware(mw),
    )
    assert Counter(mw.hist) == Counter(dict(on_start=40, on_failure=19))


@pytest.mark.asyncio
async def test_FrequencyMiddleware() -> None:
    switch = False

    async def handler(msg: str) -> None:
        nonlocal switch
        switch = not switch
        if switch:
            1/0

    mw = MockMiddleware()
    await run_actor(
        handler, ['hi'] * 40,
        walnats.middlewares.FrequencyMiddleware(mw),
    )
    assert Counter(mw.hist) == Counter(dict(on_success=1, on_failure=1, on_start=1))


@pytest.mark.asyncio
async def test_StatsdMiddleware(udp_server: UDPLogProtocol) -> None:
    from datadog.dogstatsd import DogStatsd

    switch = False

    async def handler(msg: str) -> None:
        nonlocal switch
        switch = not switch
        if switch:
            1/0

    client = DogStatsd(port=udp_server.port, disable_telemetry=True)
    await run_actor(
        handler, ['hi'] * 40,
        walnats.middlewares.StatsdMiddleware(client),
    )
    expected = [
        (r'walnats\..+\..+\.started:1\|c', 16),
        (r'walnats\..+\..+\.failed:1\|c', 2),
        (r'walnats\..+\..+\.processed:1\|c', 1),
        (r'walnats\..+\..+\.duration:0.\d+\|h', 1),
    ]
    fuzzy_match_counter(udp_server.hist, expected)


@pytest.mark.asyncio
async def test_PrometheusMiddleware() -> None:
    switch = False

    async def handler(msg: str) -> None:
        nonlocal switch
        switch = not switch
        if switch:
            1/0

    await run_actor(
        handler, ['hi'] * 40,
        walnats.middlewares.PrometheusMiddleware(),
    )


@pytest.mark.asyncio
async def test_SentryMiddleware() -> None:
    await run_actor(explode, 'hi', walnats.middlewares.SentryMiddleware())


@pytest.mark.skipif(not SENTRY_DSN, reason='SENTRY_DSN env var is not provided')
@pytest.mark.asyncio
async def test_SentryMiddleware_real_sentry() -> None:
    with sentry_sdk.init(SENTRY_DSN):
        await run_actor(explode, 'hi', walnats.middlewares.SentryMiddleware())
        sentry_sdk.flush()
