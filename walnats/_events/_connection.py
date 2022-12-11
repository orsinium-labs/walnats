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
MSG_ID = nats.js.api.Header.MSG_ID.value


@dataclass(frozen=True)
class ConnectedEvents:
    """A registry of :class:`walnats.Event` instances.

    Like :class:`walnats.Events` but connected to Nats server.

    Use it to emit events. Don't instanciate directly,
    use :meth:`walnats.Events.connect` instead.
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

    async def emit(self, event: Event[T], message: T, uid: str | None = None) -> None:
        """Send an :class:`walnats.Event` into Nats. The event must be registered first.

        Args:
            event: registered event to which the message belongs.
            message: the message payload to send.
            uid: unique ID of the message. If provided, will be used to ensure
                that the same message is not delivered twice.
                Duplicate messagess with the same ID will be ignored.
                Deduplication window in Nats JetStream is 2 minutes by default.
        """
        payload = event.encode(message)
        headers = {MSG_ID: uid} if uid is not None else None
        await self._nc.publish(event.subject_name, payload, headers=headers)

    async def request(
        self,
        event: EventWithResponse[T, R],
        message: T,
        timeout: float = 3,
    ) -> R:
        payload = event.encode(message)
        inbox = self._nc.new_inbox()
        sub = await self._nc.subscribe(inbox)
        try:
            await self._nc.publish(
                event.subject_name,
                payload,
                # We can't use Nats built-in request/reply mechanism
                # because JetStream discards the Reply header for messages.
                headers={'Walnats-Reply': inbox},
            )
            msg = await sub.next_msg(timeout=timeout)
        finally:
            await sub.unsubscribe()
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
