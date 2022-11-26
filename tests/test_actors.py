from __future__ import annotations

import asyncio
import time
from contextlib import contextmanager

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
        await asyncio.gather(
            sub_conn.listen(burst=True, **kwargs),
            *[pub_conn.emit(e, m) for e, m in messages],
        )


@contextmanager
def duration_between(min_dur: float, max_dur: float):
    start = time.perf_counter()
    yield
    actual_dur = time.perf_counter() - start
    assert min_dur <= actual_dur < max_dur


@pytest.mark.asyncio
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
    assert set(received) == set(messages)


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_run_in_process_pool() -> None:
    messages = [f'msg{i}' for i in range(20)]

    e = walnats.Event(get_random_name(), str)
    with duration_between(.1, .4):
        await run_burst(
            walnats.Actor(get_random_name(), e, slow_handler, execute_in='process'),
            messages=[(e, m) for m in messages],
            batch=len(messages),
        )


@pytest.mark.asyncio
async def test_run_in_thread_pool() -> None:
    messages = [f'msg{i}' for i in range(20)]

    e = walnats.Event(get_random_name(), str)
    with duration_between(.1, .4):
        await run_burst(
            walnats.Actor(get_random_name(), e, slow_handler, execute_in='thread'),
            messages=[(e, m) for m in messages],
            batch=len(messages),
        )


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
