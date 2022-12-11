from __future__ import annotations

from typing import TYPE_CHECKING, Coroutine


if TYPE_CHECKING:
    from .._context import Context, ErrorContext, OkContext


class Middleware:
    """Middlewares are callbacks that are triggered whe handling a message.

    In many cases, like when you want to suppress specific errors from the handler,
    you should use decorators on handlers instead of middlewares. Middlewares are useful
    when you need an additional context, like how many times the event was retried.

    Hooks can be both sync and async. In both cases, be mindful that they run
    in the same thread as the main scheduler for the important tasks. So, every
    hook must be fast and safe.
    """
    __slots__ = ()

    def on_start(self, ctx: Context) -> Coroutine[None, None, None] | None:
        """Triggered right before running the handler.

        If asynchronous, it can be executed when handler is already running
        or even finished.
        """
        pass

    def on_failure(self, ctx: ErrorContext) -> Coroutine[None, None, None] | None:
        """Triggered if the handler failed with an exception.

        If asynchronous, it can be executed when already outside of the `except` block,
        and so the traceback might not be available.

        It is possible for on_failure to be triggered before on_start.
        For example, if message decoding fails.
        """
        pass

    def on_success(self, ctx: OkContext) -> Coroutine[None, None, None] | None:
        """Triggered when the handler successfully processed the message.
        """
        pass
