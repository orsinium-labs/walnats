from __future__ import annotations
import asyncio
from contextlib import contextmanager
import time

import pytest
import walnats


async def run_burst(
    *actors: walnats.Actor,
    messages: list[tuple[walnats.Event[str], str]],
    **kwargs,
) -> None:
    events_names = set()
    events = []
    for e, _ in messages:
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
def faster_than(max_dur: float):
    start = time.perf_counter()
    try:
        yield
    finally:
        assert time.perf_counter() - start < max_dur


@pytest.mark.asyncio
async def test_many_messages_one_event() -> None:
    received = []
    messages = [f'msg{i}' for i in range(20)]

    async def handler(e: str) -> None:
        # await asyncio.sleep(.01)
        received.append(e)

    e = walnats.Event('event', str)
    with faster_than(.02):
        await run_burst(
            walnats.Actor('handler', e, handler),
            messages=[(e, m) for m in messages],
            batch=20,
        )
    assert set(received) == set(messages)
