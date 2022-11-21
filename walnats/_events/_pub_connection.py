from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, TypeVar

import nats
import nats.js

from ._event import BaseEvent, Event, EventWithResponse


T = TypeVar('T')
R = TypeVar('R')


@dataclass(frozen=True)
class PubConnection:
    _nc: nats.NATS
    _js: nats.js.JetStreamContext
    _events: tuple[BaseEvent, ...]

    async def register(self) -> None:
        """Create Nats JetStream streams for registered events.
        """
        assert self._events
        tasks = []
        for event in self._events:
            task = asyncio.create_task(event._add(self._js))
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def emit(self, event: Event[T], message: T) -> None:
        """Send an event into Nats. The event must be registered first.
        """
        payload = event.serializer.encode(message)
        await self._nc.publish(event.subject_name, payload)

    async def _request(self, event: EventWithResponse[T, R], message: T) -> R:
        payload = event.serializer.encode(message)
        msg = await self._nc.request(event.subject_name, payload)
        resp = event.response_serializer.decode(msg.data)
        return resp

    async def monitor(self) -> AsyncIterator[object]:
        """Listen to all registered events and emit them.

        Events emitted while you don't listen won't be remembered.
        In other words, it's a live feed. Useful for debugging.
        """
        queue: asyncio.Queue[object] = asyncio.Queue()
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
