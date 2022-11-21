from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

import nats

from ._pub_connection import PubConnection


if TYPE_CHECKING:
    from ._event import BaseEvent


DEFAULT_SERVER = 'nats://localhost:4222'


class Events:
    __slots__ = ['_events']
    _events: tuple[BaseEvent, ...]

    def __init__(self, *events: BaseEvent) -> None:
        assert events
        self._events = events

    @asynccontextmanager
    async def connect(
        self,
        servers: list[str] | str = DEFAULT_SERVER,
    ) -> AsyncIterator[PubConnection]:
        assert servers
        connection = await nats.connect(servers)
        async with connection:
            js = connection.jetstream()
            yield PubConnection(connection, js, self._events)
