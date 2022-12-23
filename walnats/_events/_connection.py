from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Iterator, TypeVar

import nats
import nats.js

from .._constants import HEADER_DELAY, HEADER_ID, HEADER_REPLY, HEADER_TRACE
from ._cloud_event import CloudEvent
from ._event import BaseEvent, Event, EventWithResponse


T = TypeVar('T')
R = TypeVar('R')


@dataclass(frozen=True)
class ConnectedEvents:
    """A registry of :class:`walnats.Event` instances.

    Like :class:`walnats.Events` but connected to Nats server.

    Use it to emit events. Don't instanciate directly,
    use :meth:`walnats.Events.connect` instead.

    ::

        async with events.connect() as conn:
            await conn.register()
            await conn.emit(USER_CREATED, user)
    """
    _nc: nats.NATS
    _js: nats.js.JetStreamContext
    _events: tuple[BaseEvent, ...]
    _now: Callable[[], float] = field(default=lambda: datetime.utcnow().timestamp())

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

    async def emit(
        self,
        event: Event[T],
        message: T,
        uid: str | None = None,
        trace_id: str | None = None,
        delay: float | None = None,
        meta: CloudEvent | dict[str, str] | None = None,
    ) -> None:
        """Send an :class:`walnats.Event` into Nats. The event must be registered first.

        Args:
            event: registered event to which the message belongs.
            message: the message payload to send.
            uid: unique ID of the message. If provided, will be used to ensure
                that the same message is not delivered twice.
                Duplicate messagess with the same ID will be ignored.
                Deduplication window in Nats JetStream is 2 minutes by default.
            trace_id: the ID of the request to use for distributed tracing.
                It doesn't have any effect on actors but can be used by tracing
                middlewares, such as :class:`walnats.middlewares.ZipkinMiddleware`.
            delay: the minimum delay from now before the message can be processed
                by an actor (in seconds). Internally, the message will be first delivered
                to the actor immediately and the actor will put the message back with
                the delay without triggering the handler or any middlewares.
            meta: either a dict of headers to include in Nats message
                or :class:`walnats.CloudEvent` to include headers described by
                CloudEvents spec. Keep in mind that the spec for Nats is still WIP.
                This meta information doesn't get into the handler but can be used
                by middlewares or third-party tools.
        """
        assert event in self._events
        payload = event.encode(message)
        headers = self._make_headers(
            uid=uid,
            trace_id=trace_id,
            delay=delay,
            meta=meta,
            reply=None,
        )
        await self._nc.publish(event.subject_name, payload, headers=headers or None)

    async def request(
        self,
        event: EventWithResponse[T, R],
        message: T,
        uid: str | None = None,
        trace_id: str | None = None,
        delay: float | None = None,
        meta: CloudEvent | dict[str, str] | None = None,
        timeout: float = 3,
    ) -> R:
        assert event in self._events
        payload = event.encode(message)
        inbox = self._nc.new_inbox()
        headers = self._make_headers(
            uid=uid,
            trace_id=trace_id,
            delay=delay,
            meta=meta,
            reply=inbox,
        )
        sub = await self._nc.subscribe(inbox)
        try:
            await self._nc.publish(event.subject_name, payload, headers=headers)
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

    def _make_headers(
        self, *,
        uid: str | None,
        trace_id: str | None,
        delay: float | None,
        meta: CloudEvent | dict[str, str] | None,
        reply: str | None,
    ) -> dict[str, str]:
        # generate headers
        if meta is None:
            headers = {}
        elif isinstance(meta, dict):
            headers = meta.copy()
        else:
            headers = meta.as_headers()
        if uid is not None:
            headers[HEADER_ID] = uid
        elif isinstance(meta, CloudEvent) and meta.id:
            headers[HEADER_ID] = meta.id
        if trace_id is not None:
            headers[HEADER_TRACE] = trace_id
        if delay is not None:
            headers[HEADER_DELAY] = f'{self._now() + delay}'

        # We can't use Nats built-in request/reply mechanism
        # because JetStream uses the Reply header for ack/nak.
        if reply is not None:
            headers[HEADER_REPLY] = reply

        return headers
