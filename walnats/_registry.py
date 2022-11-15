from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

import nats
from ._sub_connection import SubConnection
from ._pub_connection import PubConnection
if TYPE_CHECKING:
    from ._event import Event
    from ._actor import Actor


@dataclass(frozen=True)
class Events:
    _events: list[Event]

    def add_event(self, event: Event) -> None:
        self._events.append(event)

    async def connect(self, servers: list[str]) -> PubConnection:
        nc = await nats.connect(servers)
        js = nc.jetstream()
        return PubConnection(nc, js, self._events)


@dataclass(frozen=True)
class Actors:
    _actors: list[Actor]

    def add_actor(self, actor: Actor) -> None:
        self._actors.append(actor)

    async def connect(self, servers: list[str]) -> SubConnection:
        nc = await nats.connect(servers)
        js = nc.jetstream()
        return SubConnection(js, self._actors)
