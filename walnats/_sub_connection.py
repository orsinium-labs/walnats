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
        max_polls: int | None = None,
        poll_delay: float = 2,
        batch: int = 1,
        max_workers: int = 16,
    ) -> None:
        """Listen Nats for events for all registered actors.

        Args:
            burst: try polling events for all actors only once, handle everything polled,
                and exit. It's useful for testing when you know there is alread a message
                in the queue when you start listening, and that's all you want to process.
            max_polls: how many polling requests can be active simultaneously.
                Default to the number of actors. You might want to set it to a lower
                value if you have more actors than free network sockets in the system.
                Then actors will take turns to polling, each turn taking poll_delay.
            poll_delay: how long each poll request will wait for messages.
                Low values will produce more requests but work better with low max_polls
                and better detect broken connections. See "keepalive" on wiki.
            batch: how many messages (max) to pull in a single poll request.
                Higher values reduce the number of network requests (and so give better
                performance) but can result in messages that wait on a specific instance
                for a worker to be available while they could be delivered to another
                instance. In other words, leave it 1 (default) if you scale horizontally.
            max_workers: how many workers (handlers) can be running at the same time.
                Higher values put more strain on CPU but give better performance
                if the handlers are IO-bound and use a lot of async/await.
        """
        poll_sem = asyncio.Semaphore(max_polls or len(self._actors))
        worker_sem = asyncio.Semaphore(max_workers)
        tasks: list[asyncio.Task] = []
        for actor in self._actors:
            coro = actor._listen(
                js=self._js,
                burst=burst,
                poll_sem=poll_sem,
                worker_sem=worker_sem,
                batch=batch,
                poll_delay=poll_delay,
            )
            task = asyncio.create_task(coro)
            tasks.append(task)
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
