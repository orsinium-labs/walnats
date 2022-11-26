from __future__ import annotations

from typing import TYPE_CHECKING, Coroutine


if TYPE_CHECKING:
    from .._context import Context, ErrorContext, OkContext


class BaseMiddleware:
    __slots__ = ()

    def on_start(self, ctx: Context) -> Coroutine[None, None, None] | None:
        """Triggered asynchronously right before running the handler.

        If asynchronous, it can be executed when handler is already running
        or even finished.
        """
        pass

    def on_failure(self, ctx: ErrorContext) -> Coroutine[None, None, None] | None:
        pass

    def on_success(self, ctx: OkContext) -> Coroutine[None, None, None] | None:
        pass
