from __future__ import annotations

import logging
from functools import wraps
from typing import Awaitable, Callable, TypeVar


DEFAULT_LOGGER = logging.getLogger(__package__)
E = TypeVar('E')


class suppress:
    """Ignore specified exceptions.

    Useful for avoiding retries for errors that cannot be retried.
    Avoid using it for flow control.

    ::

        @walnats.decorators.suppress(NotFoundError)
        async def update_parcel_status(event: ParcelDiff) -> None:
            ...

    Args:
        excs: exception types to suppress.
        logger: logger to use to log suppressed exceptions. If None, no logs
            will be written, the exception will be just silently discarded.
    """
    __slots__ = ('_excs', '_logger')
    _excs: tuple[type[BaseException], ...]
    _logger: logging.Logger | logging.LoggerAdapter | None

    def __init__(
        self,
        exc: type[BaseException],
        *excs: type[BaseException],
        logger: logging.Logger | logging.LoggerAdapter | None = DEFAULT_LOGGER,
    ) -> None:
        self._excs = (exc,) + excs
        self._logger = logger

    def __call__(
        self,
        handler: Callable[[E], None | Awaitable[None]],
    ) -> Callable[[E], Awaitable[None]]:
        @wraps(handler)
        async def wrapper(event: E) -> None:
            try:
                result = handler(event)
                if result is not None:
                    await result
            except self._excs:
                if self._logger is not None:
                    self._logger.exception(
                        'suppressed exception in handler',
                        extra={'handler': handler.__name__},
                    )

        return wrapper
