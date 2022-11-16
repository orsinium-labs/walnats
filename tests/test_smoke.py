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
    pub_conn = await events.connect()
    await pub_conn.register()
    message = Model.construct(name='mark', age=32)

    received: Model | None = None

    async def handler(event: Model) -> None:
        nonlocal received
        received = event

    actor = walnats.Actor(get_random_name(), event, handler)
    actors = walnats.Actors(actor)
    sub_conn = await actors.connect()
    await sub_conn.register()

    await pub_conn.emit(event, message)
    await sub_conn.listen(stop_after=1)

    assert received == message
