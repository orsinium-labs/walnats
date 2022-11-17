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
        self, *,
        burst: bool = False,
        max_polls: int = 100,
        max_workers: int = 100,
        batch: int = 1,
    ) -> None:
        poll_sem = asyncio.Semaphore(max_polls)
        worker_sem = asyncio.Semaphore(max_workers)
        tasks: list[asyncio.Task] = []
        for actor in self._actors:
            coro = actor._listen(
                js=self._js,
                burst=burst,
                poll_sem=poll_sem,
                worker_sem=worker_sem,
                batch=batch,
            )
            task = asyncio.create_task(coro)
            tasks.append(task)
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
