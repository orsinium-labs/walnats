from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

import nats
import nats.js

if TYPE_CHECKING:
    from ._actor import Actor


@dataclass(frozen=True)
class SubConnection:
    _js: nats.js.JetStreamContext
    _actors: tuple[Actor, ...]

    async def register_actors(self) -> None:
        tasks = []
        for actor in self._actors:
            task = asyncio.create_task(actor._add(self._js))
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def listen(self) -> None:
        tasks = [asyncio.create_task(a._listen(self._js)) for a in self._actors]
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
