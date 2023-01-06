from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from enum import Enum
from typing import AsyncIterator


class Priority(Enum):
    """Priority denotes how fast an Actor can acquire the mutex.

    Actors with a higher priority start faster when the number of concurrent jobs
    reaches the value specified by ``max_jobs`` argument of
    :meth:`walnats.types.ConnectedActors.listen` method.

    ::

        SEND_EMAIL = walnats.Actor(
            'send-email', USER_CREATED, send_email,
            priority=walnats.Priority.HIGH,
        )

    """

    HIGH = 0
    """Start as soon as possible."""

    NORMAL = 1
    """Start if there are no HIGH priority actors."""

    LOW = 2
    """Start if there are no HIGH or NORMAL priority actors."""

    @asynccontextmanager
    async def acquire(self, sem: asyncio.Semaphore) -> AsyncIterator[None]:
        """Acquire semaphore with priority.
        """
        for _ in range(self.value):
            async with sem:
                await asyncio.sleep(0)
        async with sem:
            yield
