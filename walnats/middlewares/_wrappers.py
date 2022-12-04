from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Coroutine

from ._base import Middleware


if TYPE_CHECKING:
    from .._context import Context, ErrorContext, OkContext


@dataclass
class ErrorThresholdMiddleware(Middleware):
    """
    Trigger on_failure of the wrapped middleware only if there are too many
    sequential errors.

    The errors are counted per actor, per message, and overall.
    The counter is reset when there is at least one successfully processed message.

    Args:
        middleware: wrapped middleware to triger when errors accumulate.
        total_failures: how many errors have to accumulate over all actors
            before the on_failure of the wrapped middleware is triggered.
            Use it to detect when the whole system is unhealthy.
        actor_failures: how many errors have to accumulate in a single actor
            before the on_failure of the wrapped middleware is triggered.
            Use it to detect an unhealthy actor.
        message_failures: how many times the message have to fail
            before on_failure of the wrapped middleware is triggered.
            Use it to detect an unhealthy message.
    """
    middleware: Middleware
    total_failures: int = 20
    actor_failures: int = 20
    message_failures: int = 20

    _overall: int = 0
    _per_actor: dict[str, int] = field(default_factory=dict)

    def on_start(self, ctx: Context) -> Coroutine[None, None, None] | None:
        return self.middleware.on_start(ctx)

    def on_success(self, ctx: OkContext) -> Coroutine[None, None, None] | None:
        self._overall = 0
        del self._per_actor[f'{ctx.actor.event.name}.{ctx.actor.name}']
        return self.middleware.on_success(ctx)

    def on_failure(self, ctx: ErrorContext) -> Coroutine[None, None, None] | None:
        actor_name = f'{ctx.actor.event.name}.{ctx.actor.name}'
        if self._overall > self.total_failures:
            return self.middleware.on_failure(ctx)
        if self._per_actor.setdefault(actor_name, 0) > self.actor_failures:
            return self.middleware.on_failure(ctx)
        if (ctx.metadata.num_delivered or 0) >= self.message_failures:
            return self.middleware.on_failure(ctx)
        self._overall += 1
        self._per_actor[actor_name] += 1
        return None
