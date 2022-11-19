from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

import nats

from ._pub_connection import PubConnection
from ._sub_connection import SubConnection

if TYPE_CHECKING:
    from ._actor import Actor
    from ._event import Event


DEFAULT_SERVER = 'nats://localhost:4222'


class Events:
    __slots__ = ['_events']
    _events: tuple[Event, ...]

    def __init__(self, *events: Event) -> None:
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


class Actors:
    __slots__ = ['_actors']
    _actors: tuple[Actor, ...]

    def __init__(self, *actors: Actor) -> None:
        assert actors
        self._actors = actors

    @asynccontextmanager
    async def connect(
        self,
        servers: list[str] | str = DEFAULT_SERVER,
    ) -> AsyncIterator[SubConnection]:
        assert servers
        connection = await nats.connect(servers)
        async with connection:
            js = connection.jetstream()
            yield SubConnection(js, self._actors)
