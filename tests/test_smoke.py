from __future__ import annotations

import pydantic
import pytest

import walnats

from .helpers import get_random_name


class Model(pydantic.BaseModel):
    name: str
    age: int


@pytest.mark.asyncio
async def test_smoke() -> None:
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
        await pub_conn.emit(event, message)
        await sub_conn.listen(burst=True)

    assert received == message
