from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from .._context import Context, ErrorContext, OkContext


M = TypeVar('M')


class BaseAsyncMiddleware(Generic[M]):
    __slots__ = ()

    async def on_start(self, ctx: Context[M]) -> None:
        """Triggered asynchronously right before running the handler.

        Since it is asynchronous, it can be executed when handler is already running
        or even finished.
        """
        pass

    async def on_failure(self, ctx: ErrorContext[M]) -> None:
        pass

    async def on_success(self, ctx: OkContext[M]) -> None:
        pass


class BaseSyncMiddleware(Generic[M]):
    __slots__ = ()

    def on_start(self, ctx: Context[M]) -> None:
        """Triggered right before running the handler.
        """
        pass

    def on_failure(self, ctx: ErrorContext[M]) -> None:
        pass

    def on_success(self, ctx: OkContext[M]) -> None:
        pass
