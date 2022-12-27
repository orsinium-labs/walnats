from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import walnats

from ..helpers import get_random_name


if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


async def noop(*args) -> None:
    return None


@pytest.mark.skip
async def test_scheduler(event: walnats.Event, monkeypatch: MonkeyPatch):
    received = []

    def handler(event) -> None:
        received.append(event)

    e = event.with_schedule()
    a = walnats.Actor(get_random_name(), e, handler)
    actors = walnats.Actors(a)
    events = walnats.Events(e)

    monkeypatch.setattr('walnats._events._scheduler.asyncio.sleep', noop)
    async with actors.connect() as acon, events.connect() as econ:
        await econ.register()
        await acon.register()
        await walnats.Scheduler().run(econ, burst=True)
        await acon.listen(burst=True)
    assert len(received) == 1
