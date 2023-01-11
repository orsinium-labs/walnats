from __future__ import annotations

import asyncio
import time

import pytest

import walnats

from ..helpers import duration_between, get_random_name, run_burst


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
            walnats.Actor(
                get_random_name(), e, slow_handler,
                execute_in=walnats.ExecuteIn.PROCESS,
            ),
            messages=[(e, m) for m in messages],
            batch=len(messages),
        )


async def test_run_in_thread_pool() -> None:
    messages = [f'msg{i}' for i in range(20)]

    e = walnats.Event(get_random_name(), str)
    with duration_between(.1, .4):
        await run_burst(
            walnats.Actor(
                get_random_name(), e, slow_handler,
                execute_in=walnats.ExecuteIn.THREAD,
            ),
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


async def test_consume_many_messages_without_burst() -> None:
    received = []

    async def handler(e: str) -> None:
        await asyncio.sleep(.005)
        received.append(e)

    e = walnats.Event(get_random_name(), str)
    a = walnats.Actor(get_random_name(), e, handler)
    events = walnats.Events(e)
    actors = walnats.Actors(a)
    async with events.connect() as pub_conn, actors.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await pub_conn.emit(e, 'hi')
        await asyncio.sleep(.01)
        task = asyncio.create_task(sub_conn.listen())
        await asyncio.sleep(.01)
        await pub_conn.emit(e, 'hi')
        await asyncio.sleep(.01)
        task.cancel()
        assert len(received) == 2


@pytest.mark.parametrize('pulse', [True, False])
async def test_pulse(pulse: bool) -> None:
    received = []
    first_run = True

    async def handler(e: str) -> None:
        nonlocal first_run
        received.append(e)
        if first_run:
            first_run = False
            await asyncio.sleep(10)

    e = walnats.Event(get_random_name(), str)
    a = walnats.Actor(get_random_name(), e, handler, ack_wait=.1, pulse=pulse)
    events = walnats.Events(e)
    actors = walnats.Actors(a)
    async with events.connect() as pub_conn, actors.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await pub_conn.emit(e, 'hi')
        await asyncio.sleep(.01)
        task = asyncio.create_task(sub_conn.listen())
        await asyncio.sleep(.2)
        task.cancel()
        if pulse:
            assert len(received) == 1
        else:
            assert len(received) == 2


async def test_with_response_but_regular_emit() -> None:
    """
    If an actor is subscribed to an event with a response,
    it's still possible for the actor to receive a copy of this event
    without response expected. In such case, we just expect the code not to explode.
    """
    received = []

    async def handler(e: str) -> int:
        await asyncio.sleep(.1)
        received.append(e)
        return 1

    e = walnats.Event(get_random_name(), str)
    er = e.with_response(int)
    a = walnats.Actor(get_random_name(), er, handler)
    events = walnats.Events(e)
    actors = walnats.Actors(a)
    async with events.connect() as pub_conn, actors.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await pub_conn.emit(e, 'hi')
        await asyncio.sleep(.01)
        await sub_conn.listen(burst=True)
        assert len(received) == 1


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
    e = walnats.Event('e', str)
    a = walnats.Actor('a', e, lambda _: None, retry_delay=delays)
    assert a._get_nak_delay(attempt) == expected
