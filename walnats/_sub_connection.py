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

    async def register(self) -> None:
        """Add nats consumers for actors.
        """
        tasks = []
        for actor in self._actors:
            task = asyncio.create_task(actor._add(self._js))
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def listen(
        self,
        stop_after: int = 0,
        workers: int = 100,
    ) -> None:
        sem = asyncio.Semaphore(workers)
        tasks: list[asyncio.Task] = []
        for actor in self._actors:
            coro = actor._listen(js=self._js, stop_after=stop_after, sem=sem)
            task = asyncio.create_task(coro)
            tasks.append(task)
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
