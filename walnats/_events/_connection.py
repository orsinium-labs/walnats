from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, TypeVar

import nats
import nats.js

from ._event import BaseEvent, Event, EventWithResponse


T = TypeVar('T')
R = TypeVar('R')


@dataclass(frozen=True)
class ConnectedEvents:
    """A registry of Event instances. Like Events but connected to Nats server.

    Use it to emit events. Don't instanciate directly, use Events.connect instead.
    """
    _nc: nats.NATS
    _js: nats.js.JetStreamContext
    _events: tuple[BaseEvent, ...]

    async def register(self) -> None:
        """Create Nats JetStream streams for registered events.
        """
        assert self._events
        tasks = []
        for event in self._events:
            task = asyncio.create_task(
                event._add(self._js),
                name=f'events/{event.name}/add',
            )
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def emit(self, event: Event[T], message: T) -> None:
        """Send an event into Nats. The event must be registered first.
        """
        payload = event.encode(message)
        await self._nc.publish(event.subject_name, payload)

    async def _request(self, event: EventWithResponse[T, R], message: T) -> R:
        payload = event.encode(message)
        msg = await self._nc.request(event.subject_name, payload)
        resp = event.decode_response(msg.data)
        return resp

    @contextmanager
    def monitor(self) -> Iterator[asyncio.Queue[object]]:
        """Listen to all registered events and iterate over them.

        Events emitted while you don't listen won't be remembered.
        In other words, it's a live feed. Useful for debugging.
        """
        queue: asyncio.Queue[object] = asyncio.Queue()
        tasks: list[asyncio.Task] = []
        for event in self._events:
            task = asyncio.create_task(
                event._monitor(self._nc, queue),
                name=f'events/{event.name}/monitor',
            )
            tasks.append(task)
        try:
            yield queue
        finally:
            for task in tasks:
                task.cancel()
