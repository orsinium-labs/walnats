from __future__ import annotations

import asyncio

import pytest

import walnats

from .helpers import get_random_name


async def run_actor(
    actor: walnats.Actor[str, None],
    message: str,
    **kwargs,
) -> None:
    assert isinstance(actor.event, walnats.Event)
    events_reg = walnats.Events(actor.event)
    actors_reg = walnats.Actors(actor)
    async with events_reg.connect() as pub_conn, actors_reg.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await asyncio.gather(
            sub_conn.listen(burst=True, **kwargs),
            pub_conn.emit(actor.event, message),
        )


@pytest.mark.asyncio
async def test_custom_sync() -> None:
    triggered = []

    class Middleware(walnats.middlewares.BaseSyncMiddleware):
        def on_failure(self, ctx: walnats.types.ErrorContext) -> None:
            triggered.append('on_failure')

        def on_start(self, ctx: walnats.types.Context) -> None:
            triggered.append('on_start')

        def on_success(self, ctx: walnats.types.OkContext) -> None:
            triggered.append('on_success')

    async def handler(msg: str) -> None:
        assert msg == 'hi'
        triggered.append('handler')

    e = walnats.Event(get_random_name(), str)
    a = walnats.Actor(get_random_name(), e, handler, sync_middlewares=(Middleware(),))
    await run_actor(a, 'hi')
    assert triggered == ['on_start', 'handler', 'on_success']


@pytest.mark.asyncio
async def test_custom_sync__on_failure() -> None:
    triggered = []

    class Middleware(walnats.middlewares.BaseSyncMiddleware):
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

    e = walnats.Event(get_random_name(), str)
    a = walnats.Actor(get_random_name(), e, handler, sync_middlewares=(Middleware(),))
    await run_actor(a, 'hi')
    assert triggered == ['on_start', 'handler', 'on_failure']


@pytest.mark.asyncio
async def test_custom_async() -> None:
    triggered = []

    class Middleware(walnats.middlewares.BaseAsyncMiddleware):
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

    e = walnats.Event(get_random_name(), str)
    a = walnats.Actor(get_random_name(), e, handler, async_middlewares=(Middleware(),))
    await run_actor(a, 'hi')
    assert len(triggered) == 3
    assert set(triggered) == {'on_start', 'handler', 'on_success'}


@pytest.mark.asyncio
async def test_custom_async__on_failure() -> None:
    triggered = []

    class Middleware(walnats.middlewares.BaseAsyncMiddleware):
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

    e = walnats.Event(get_random_name(), str)
    a = walnats.Actor(get_random_name(), e, handler, async_middlewares=(Middleware(),))
    await run_actor(a, 'hi')
    assert len(triggered) == 3
    assert set(triggered) == {'on_start', 'handler', 'on_failure'}
