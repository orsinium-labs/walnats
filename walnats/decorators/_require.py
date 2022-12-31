from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from functools import wraps
from typing import Awaitable, Callable, TypeVar


DEFAULT_LOGGER = logging.getLogger(__package__)
E = TypeVar('E')


@dataclass(frozen=True)
class require:
    """Require the predicate to be true before the handler can be called.

    If the predicate is not true, the handler invocation will be delayed.
    Useful for waiting for dependencies. For example, to make sure the handler does not
    start before a connection to the database is established.

    ::

        @walnats.decorators.require(db.is_connected)
        async def write_audit_log(record: LogRecord) -> None:
            await db.save_record(record)

    Args:
        predicate: callable that indicates if the handler can be called.
        pause: delay (in seconds) between each check of the predicate.
    """
    predicate: Callable[[], bool]
    pause: float = 0

    def __call__(
        self,
        handler: Callable[[E], None | Awaitable[None]],
    ) -> Callable[[E], Awaitable[None]]:
        @wraps(handler)
        async def wrapper(event: E) -> None:
            while not self.predicate():
                await asyncio.sleep(self.pause)
            result = handler(event)
            if result is not None:
                await result
        return wrapper
