from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import Awaitable, Callable, TypeVar, overload


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

    @overload
    def __call__(
        self,
        handler: Callable[[E], None],
    ) -> Callable[[E], None]:
        pass

    @overload
    def __call__(
        self,
        handler: Callable[[E], Awaitable[None]],
    ) -> Callable[[E], Awaitable[None]]:
        pass

    def __call__(
        self,
        handler: Callable[[E], None | Awaitable[None]],
    ) -> Callable[[E], None | Awaitable[None]]:
        if asyncio.iscoroutinefunction(handler):
            return self._bind_async(handler)
        return self._bind_sync(handler)

    def _bind_async(
        self,
        handler: Callable[[E], Awaitable[None]],
    ) -> Callable[[E], Awaitable[None]]:
        """Wrap an async function.

        We can't only return a snc function that handles both sync and async code
        because we want ``asyncio.iscoroutinefunction`` to produce the same result
        on the wrapped and the original functions.
        """
        @wraps(handler)
        async def wrapper(event: E) -> None:
            try:
                return await handler(event)
            except self._excs:
                self._log(handler)

        return wrapper

    def _bind_sync(
        self,
        handler: Callable[[E], Awaitable[None] | None],
    ) -> Callable[[E], Awaitable[None] | None]:
        """Wrap a regular function.

        Keep in mind that a sync function can return an awaitable.
        Actor does support it, and so the decorator should too.
        """
        @wraps(handler)
        def wrapper(event: E) -> Awaitable[None] | None:
            try:
                result = handler(event)
            except self._excs:
                self._log(handler)
                return None
            if result is not None:
                return self._wrap_awaitable(result, handler)
            return result

        return wrapper

    async def _wrap_awaitable(
        self,
        awaitable: Awaitable[None],
        handler: Callable[[E], Awaitable[None] | None],
    ) -> None:
        try:
            await awaitable
        except self._excs:
            self._log(handler)

    def _log(self, handler: Callable) -> None:
        if self._logger is not None:
            self._logger.exception(
                'suppressed exception in handler',
                extra={'handler': handler.__name__},
            )
        return None
