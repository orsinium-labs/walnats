from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator, Iterator

import nats

from ._connection import ConnectedEvents


if TYPE_CHECKING:
    from ._event import BaseEvent


DEFAULT_SERVER = 'nats://localhost:4222'


class Events:
    """Registry of :class:`walnats.Event` instances.

    ::

        events = walnats.Events(event1, event2, event3)
        async with events.connect() as conn:
            ...
    """
    __slots__ = ('_events',)
    _events: tuple[BaseEvent, ...]

    def __init__(self, *events: BaseEvent) -> None:
        assert events
        self._events = events

    def get(self, name: str) -> BaseEvent | None:
        """Get an :class:`walnats.Event` from the list of registered events by name.
        """
        for event in self._events:
            if event.name == name:
                return event
        return None

    def __iter__(self) -> Iterator[BaseEvent]:
        """Iterate over all registered events.
        """
        return iter(self._events)

    @asynccontextmanager
    async def connect(
        self,
        server: list[str] | str | nats.NATS = DEFAULT_SERVER,
        close: bool = True,
    ) -> AsyncIterator[ConnectedEvents]:
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
            yield ConnectedEvents(connection, js, self._events)
        finally:
            if close:
                await connection.close()
