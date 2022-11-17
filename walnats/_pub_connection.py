from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, TypeVar

import nats
import nats.js

from ._event import Event
from ._serializers import Model

M = TypeVar('M', bound=Model)


@dataclass(frozen=True)
class PubConnection:
    _nc: nats.NATS
    _js: nats.js.JetStreamContext
    _events: tuple[Event, ...]

    async def register(self) -> None:
        """Create nats streams for events.
        """
        assert self._events
        tasks = []
        for event in self._events:
            task = asyncio.create_task(event._add(self._js))
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def emit(self, event: Event[M], message: M) -> None:
        payload = event.serializer.encode(message)
        await self._nc.publish(event.subject_name, payload)

    async def monitor(self) -> AsyncIterator[Model]:
        queue: asyncio.Queue[Model] = asyncio.Queue()
        tasks: list[asyncio.Task] = []
        for event in self._events:
            task = asyncio.create_task(event._monitor(self._nc, queue))
            tasks.append(task)
        try:
            while True:
                yield await queue.get()
        finally:
            for task in tasks:
                task.cancel()
