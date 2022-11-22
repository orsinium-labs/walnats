from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .._context import Context, ErrorContext, OkContext


class BaseAsyncMiddleware:
    __slots__ = ()

    async def on_start(self, ctx: Context) -> None:
        """Triggered asynchronously right before running the handler.

        Since it is asynchronous, it can be executed when handler is already running
        or even finished.
        """
        pass

    async def on_failure(self, ctx: ErrorContext) -> None:
        pass

    async def on_success(self, ctx: OkContext) -> None:
        pass


class BaseSyncMiddleware:
    __slots__ = ()

    def on_start(self, ctx: Context) -> None:
        """Triggered right before running the handler.
        """
        pass

    def on_failure(self, ctx: ErrorContext) -> None:
        pass

    def on_success(self, ctx: OkContext) -> None:
        pass
