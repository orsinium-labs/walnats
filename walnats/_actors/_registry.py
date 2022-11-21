from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

import nats

from ._sub_connection import SubConnection


if TYPE_CHECKING:
    from ._actor import Actor


DEFAULT_SERVER = 'nats://localhost:4222'


class Actors:
    __slots__ = ['_actors']
    _actors: tuple[Actor, ...]

    def __init__(self, *actors: Actor) -> None:
        assert actors
        self._actors = actors

    @asynccontextmanager
    async def connect(
        self,
        server: list[str] | str | nats.NATS = DEFAULT_SERVER,
        close: bool = True,
    ) -> AsyncIterator[SubConnection]:
        if isinstance(server, nats.NATS):
            connection = server
        else:
            assert server
            connection = await nats.connect(server)
        try:
            js = connection.jetstream()
            yield SubConnection(js, self._actors)
        finally:
            if close:
                await connection.close()
