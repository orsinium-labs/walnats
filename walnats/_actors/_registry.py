from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator, Iterator

import nats

from ._connection import ConnectedActors


if TYPE_CHECKING:
    from ._actor import Actor


DEFAULT_SERVER = 'nats://localhost:4222'


class Actors:
    """Registry of :class:`walnats.Actor` instances.

    ::

        actors = walnats.Actors(actor1, actor2, actor3)
        async with actors.connect() as conn:
            ...
    """
    __slots__ = ['_actors']
    _actors: tuple[Actor, ...]

    def __init__(self, *actors: Actor) -> None:
        assert actors
        self._actors = actors

    def get(self, name: str) -> Actor | None:
        """Get an :class:`walnats.Actor` from the list of registered actors by name.
        """
        for actor in self._actors:
            if actor.name == name:
                return actor
        return None

    def __iter__(self) -> Iterator[Actor]:
        """Iterate over all registered actors.
        """
        return iter(self._actors)

    @asynccontextmanager
    async def connect(
        self,
        server: list[str] | str | nats.NATS = DEFAULT_SERVER,
        close: bool = True,
    ) -> AsyncIterator[ConnectedActors]:
        """Context manager that keeps connection to Nats server.

        Args:
            server: Nats server URL, list of URLs, or already connected server.
            close: Close the connection on exit from the context.
                Set to False if you explicitly pass a server instance and want
                to keep using it after leaving the context.
        """
        if isinstance(server, nats.NATS):
            connection = server
        else:
            assert server
            connection = await nats.connect(server)
        assert not connection.is_closed
        try:
            js = connection.jetstream()
            yield ConnectedActors(js, self._actors)
        finally:
            if close:
                await connection.close()
