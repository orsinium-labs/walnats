from __future__ import annotations
from typing import TYPE_CHECKING

import nats
from ._sub_connection import SubConnection
from ._pub_connection import PubConnection
if TYPE_CHECKING:
    from ._event import Event
    from ._actor import Actor


class Events:
    __slots__ = ['_events']
    _events: tuple[Event, ...]

    def __init__(self, *events: Event) -> None:
        self._events = events

    async def connect(self, servers: list[str]) -> PubConnection:
        nc = await nats.connect(servers)
        js = nc.jetstream()
        return PubConnection(nc, js, self._events)


class Actors:
    __slots__ = ['_actors']
    _actors: tuple[Actor, ...]

    def __init__(self, *actors: Actor) -> None:
        self._actors = actors

    async def connect(self, servers: list[str]) -> SubConnection:
        nc = await nats.connect(servers)
        js = nc.jetstream()
        return SubConnection(js, self._actors)
