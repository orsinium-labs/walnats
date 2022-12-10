from __future__ import annotations

import asyncio

import pydantic

import walnats

from .helpers import get_random_name


class Model(pydantic.BaseModel):
    name: str
    age: int


async def test_emit_consume() -> None:
    event = walnats.Event(get_random_name(), Model)
    events = walnats.Events(event)
    received: Model | None = None
    message = Model(name='mark', age=32)

    async def handler(event: Model) -> None:
        nonlocal received
        received = event

    actor = walnats.Actor(get_random_name(), event, handler)
    actors = walnats.Actors(actor)
    async with events.connect() as pub_conn, actors.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await asyncio.gather(
            pub_conn.emit(event, message),
            sub_conn.listen(burst=True),
        )

    assert received == message


async def test_request_response() -> None:
    event = walnats.Event(get_random_name(), str).with_response(int)
    events = walnats.Events(event)

    async def str_to_int(event: str) -> int:
        assert event == '42'
        return int(event)

    actor = walnats.Actor(get_random_name(), event, str_to_int)
    actors = walnats.Actors(actor)
    async with events.connect() as pub_conn, actors.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        task = asyncio.create_task(sub_conn.listen(burst=True))
        resp = await pub_conn.request(event, '42')
        await task
    assert resp
    assert resp == 42
