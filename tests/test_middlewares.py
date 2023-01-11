from __future__ import annotations

import asyncio
import logging
import os
import re
from collections import Counter
from typing import TYPE_CHECKING, Callable

import aiozipkin
import pytest
import sentry_sdk
from aiozipkin.transport import StubTransport

import walnats

from .helpers import UDPLogProtocol, fuzzy_match_counter, get_random_name


if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


async def noop(msg: str) -> None:
    pass


async def explode(msg: str) -> None:
    1 / 0

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
    trace_id: str | None = None,
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
        await asyncio.gather(
            *[pub_conn.emit(event, m, trace_id=trace_id) for m in messages],
        )
        if len(messages) > 1:
            await asyncio.sleep(.01)
        await sub_conn.listen(burst=True, batch=len(messages), **kwargs)


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


async def test_TextLogMiddleware(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    await run_actor(noop, 'hi', walnats.middlewares.TextLogMiddleware())
    records = []
    for record in caplog.records:
        if record.name.startswith('walnats'):
            records.append(record)
    assert len(records) == 2
    assert re.match(r'event .+: received by .+', records[0].message)
    assert re.match(r'event .+: processed by .+', records[1].message)


async def test_TextLogMiddleware__on_failure(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    await run_actor(explode, 'hi', walnats.middlewares.TextLogMiddleware())
    records = []
    for record in caplog.records:
        if record.name.startswith('walnats'):
            records.append(record)
    assert len(records) == 3
    assert re.match(r'event .+: received by .+', records[0].message)
    assert records[1].message.startswith('Unhandled ZeroDivisionError in')
    assert re.match(r'event .+: actor .+ failed', records[2].message)


async def test_ErrorThresholdMiddleware__single_failure() -> None:
    mw = MockMiddleware()
    await run_actor(explode, 'hi', walnats.middlewares.ErrorThresholdMiddleware(mw))
    assert mw.hist == ['on_start']


async def test_ErrorThresholdMiddleware__multiple_failures() -> None:
    mw = MockMiddleware()
    await run_actor(
        explode, ['hi'] * 40,
        walnats.middlewares.ErrorThresholdMiddleware(mw, total_failures=1000),
    )
    assert Counter(mw.hist) == Counter(dict(on_start=40, on_failure=19))


async def test_ErrorThresholdMiddleware__multiple_failures_many_actors() -> None:
    mw = MockMiddleware()
    emw = walnats.middlewares.ErrorThresholdMiddleware(mw, actor_failures=100)
    await asyncio.gather(
        run_actor(explode, ['hi'] * 10, emw),
        run_actor(explode, ['hi'] * 30, emw),
    )
    assert Counter(mw.hist) == Counter(dict(on_start=40, on_failure=19))


async def test_ErrorThresholdMiddleware__on_success() -> None:
    mw = MockMiddleware()
    await run_actor(noop, 'hi', walnats.middlewares.ErrorThresholdMiddleware(mw))
    assert mw.hist == ['on_start', 'on_success']


async def test_FrequencyMiddleware() -> None:
    switch = False

    async def handler(msg: str) -> None:
        nonlocal switch
        switch = not switch
        if switch:
            1 / 0

    mw = MockMiddleware()
    await run_actor(
        handler, ['hi'] * 40,
        walnats.middlewares.FrequencyMiddleware(mw),
    )
    assert Counter(mw.hist) == Counter(dict(on_success=1, on_failure=1, on_start=1))


async def test_StatsdMiddleware(udp_server: UDPLogProtocol) -> None:
    from datadog.dogstatsd import DogStatsd

    switch = False
    received = []

    async def handler(msg: str) -> None:
        nonlocal switch
        switch = not switch
        received.append(msg)
        if switch:
            1 / 0

    client = DogStatsd(port=udp_server.port, disable_telemetry=True)
    await run_actor(
        handler, ['hi'] * 40,
        walnats.middlewares.StatsdMiddleware(client),
    )
    assert len(received) == 40
    client.flush()
    await asyncio.sleep(.1)
    # remove numbers from `duration` metric, so it can be aggregated
    hist = [h.split(':0.')[0] for h in udp_server.hist]
    expected = [
        (r'walnats\..+\..+\.started:1\|c', 40),
        (r'walnats\..+\..+\.failed:1\|c', 20),
        (r'walnats\..+\..+\.processed:1\|c', 20),
        (r'walnats\..+\..+\.duration', 20),
    ]
    fuzzy_match_counter(hist, expected)


async def test_PrometheusMiddleware() -> None:
    switch = False

    async def handler(msg: str) -> None:
        nonlocal switch
        switch = not switch
        if switch:
            1 / 0

    await run_actor(
        handler, ['hi'] * 40,
        walnats.middlewares.PrometheusMiddleware(),
    )


async def test_SentryMiddleware__smoke() -> None:
    await run_actor(explode, 'hi', walnats.middlewares.SentryMiddleware())


@pytest.mark.skipif(not SENTRY_DSN, reason='SENTRY_DSN env var is not provided')
async def test_SentryMiddleware__real_sentry() -> None:
    with sentry_sdk.init(SENTRY_DSN):
        await run_actor(explode, 'hi', walnats.middlewares.SentryMiddleware())
        sentry_sdk.flush()


async def test_ZipkinMiddleware() -> None:
    endpoint = aiozipkin.create_endpoint('test_service')
    transport = StubTransport()
    async with aiozipkin.create_custom(endpoint, transport) as tracer:

        # emit a trace for normal operation
        await run_actor(noop, 'hi', walnats.middlewares.ZipkinMiddleware(tracer))
        assert len(transport.records) == 1
        r = transport.records[-1]
        tags = r.asdict()['tags']
        assert set(tags) == {'event'}

        # include exception on failure
        await run_actor(explode, 'hi', walnats.middlewares.ZipkinMiddleware(tracer))
        assert len(transport.records) == 2
        r = transport.records[-1]
        tags = r.asdict()['tags']
        assert set(tags) == {'event', 'error'}
        assert tags['error'] == 'division by zero'

        # use provided trace_id if available
        await run_actor(
            noop, 'hi', walnats.middlewares.ZipkinMiddleware(tracer),
            trace_id='123',
        )
        assert len(transport.records) == 3
        r = transport.records[-1]
        tags = r.asdict()['tags']
        assert set(tags) == {'event'}
        assert r.asdict()['traceId'] == '123'

        for r in transport.records:
            assert r.asdict()['kind'] == aiozipkin.CONSUMER


async def test_CurrentContextMiddleware() -> None:
    mw = walnats.middlewares.CurrentContextMiddleware()
    received = []

    async def handler(msg: str) -> None:
        assert msg == mw.context.message
        received.append(msg)

    await run_actor(handler, [f'{i}' for i in range(40)], mw)
    assert len(received) == 40


async def test_OpenTelemetryTraceMiddleware__smoke() -> None:
    import opentelemetry.trace

    tracer = opentelemetry.trace.get_tracer('tests')
    await run_actor(
        explode, 'hi',
        walnats.middlewares.OpenTelemetryTraceMiddleware(tracer),
    )

    tracer = opentelemetry.trace.get_tracer('tests')
    await run_actor(
        noop, 'hi',
        walnats.middlewares.OpenTelemetryTraceMiddleware(tracer),
    )
