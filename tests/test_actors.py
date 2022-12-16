from __future__ import annotations

import asyncio
import time
from contextlib import contextmanager

import nats
import pytest

import walnats

from .helpers import get_random_name


async def run_burst(
    *actors: walnats.Actor,
    messages: list[tuple[walnats.Event[str], str]],
    **kwargs,
) -> None:
    events_names = set()
    events: list[walnats.types.BaseEvent] = []
    e: walnats.types.BaseEvent
    for e, _ in messages:
        if e.name not in events_names:
            events.append(e)
            events_names.add(e.name)
    for a in actors:
        e = a.event
        if e.name not in events_names:
            events.append(e)
            events_names.add(e.name)

    events_reg = walnats.Events(*events)
    actors_reg = walnats.Actors(*actors)
    async with events_reg.connect() as pub_conn, actors_reg.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await asyncio.gather(*[pub_conn.emit(e, m) for e, m in messages])
        await asyncio.sleep(.01)
        await sub_conn.listen(burst=True, **kwargs)


@contextmanager
def duration_between(min_dur: float, max_dur: float):
    start = time.perf_counter()
    yield
    actual_dur = time.perf_counter() - start
    assert min_dur <= actual_dur < max_dur


async def test_many_messages_one_event() -> None:
    received = []
    messages = [f'msg{i}' for i in range(20)]

    async def handler(e: str) -> None:
        await asyncio.sleep(.1)
        received.append(e)

    e = walnats.Event(get_random_name(), str)
    with duration_between(0, .3):
        await run_burst(
            walnats.Actor(get_random_name(), e, handler),
            messages=[(e, m) for m in messages],
            batch=len(messages),
        )
        assert len(received) == len(messages)
        assert set(received) == set(messages)


async def test_respect_timeout() -> None:
    async def handler(e: str) -> None:
        raise AssertionError('unreachable')

    e = walnats.Event(get_random_name(), str)
    with duration_between(.1, .15):
        await run_burst(
            walnats.Actor(get_random_name(), e, handler),
            messages=[],
            poll_delay=.1,
        )


def slow_handler(e: str) -> None:
    time.sleep(.1)


async def test_run_in_process_pool() -> None:
    messages = [f'msg{i}' for i in range(20)]

    e = walnats.Event(get_random_name(), str)
    with duration_between(.1, .4):
        await run_burst(
            walnats.Actor(get_random_name(), e, slow_handler, execute_in='process'),
            messages=[(e, m) for m in messages],
            batch=len(messages),
        )


async def test_run_in_thread_pool() -> None:
    messages = [f'msg{i}' for i in range(20)]

    e = walnats.Event(get_random_name(), str)
    with duration_between(.1, .4):
        await run_burst(
            walnats.Actor(get_random_name(), e, slow_handler, execute_in='thread'),
            messages=[(e, m) for m in messages],
            batch=len(messages),
        )


async def test_delay() -> None:
    class MW(walnats.middlewares.Middleware):
        def on_start(self, ctx) -> None:
            assert ctx.attempts == 1

    received: list[str] = []
    e = walnats.Event(get_random_name(), str)
    a = walnats.Actor(get_random_name(), e, received.append, middlewares=(MW(),))
    events_reg = walnats.Events(e)
    actors_reg = walnats.Actors(a)
    async with events_reg.connect() as pub_conn, actors_reg.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()

        # emit the message with `delay` specified
        await pub_conn.emit(e, 'hi', delay=.3)
        await asyncio.sleep(.01)

        # consume the message and delay it
        with duration_between(0, .01):
            await sub_conn.listen(burst=True)
        assert received == []

        # wait for message and process it
        with duration_between(.28, .30):
            await sub_conn.listen(burst=True)
        assert received == ['hi']


def test_actors_get():
    async def noop(_):
        pass

    e = walnats.Event(get_random_name(), str)
    actors = walnats.Actors(
        walnats.Actor('a1', e, noop),
        walnats.Actor('a2', e, noop),
        walnats.Actor('a3', e, noop),
    )
    a1 = actors.get('a1')
    assert a1
    assert a1.name == 'a1'
    a2 = actors.get('a2')
    assert a2
    assert a2.name == 'a2'
    assert actors.get('something') is None


def test_actors_iter():
    async def noop(_):
        pass

    e = walnats.Event(get_random_name(), str)
    a1 = walnats.Actor('a1', e, noop)
    a2 = walnats.Actor('a3', e, noop)
    a3 = walnats.Actor('a2', e, noop)
    actors = walnats.Actors(a1, a2, a3)
    assert list(actors) == [a1, a2, a3]


@pytest.mark.parametrize('delays, attempt, expected', [
    ([], 0, 0),
    ([], 1, 0),
    ([4, 5, 6], None, 4),
    ([4, 5, 6], 0, 4),
    ([4, 5, 6], 1, 5),
    ([4, 5, 6], 2, 6),
    ([4, 5, 6], 3, 6),
    ([4, 5, 6], 13, 6),
])
def test_get_nak_delay(delays, attempt, expected):
    e = walnats.Event('', str)
    a = walnats.Actor('', e, lambda _: None, retry_delay=delays)
    assert a._get_nak_delay(attempt) == expected


async def test_actors_dont_own_connection():
    nc = await nats.connect()

    e = walnats.Event(get_random_name(), str)
    events = walnats.Events(e)
    async with events.connect(nc, close=False) as econn:
        await econn.register()
    assert not nc.is_closed

    a = walnats.Actor(get_random_name(), e, lambda _: None)
    actors = walnats.Actors(a)
    async with actors.connect(nc, close=False) as aconn:
        await aconn.register()
    assert not nc.is_closed
