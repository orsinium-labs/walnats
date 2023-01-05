from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Coroutine

from ._base import Middleware


if TYPE_CHECKING:
    from .._context import Context, ErrorContext, OkContext


@dataclass
class ErrorThresholdMiddleware(Middleware):
    """Trigger on_failure only if there are too many sequential errors.

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
    _per_actor: dict[str, int] = field(default_factory=dict, init=False)

    def on_start(self, ctx: Context) -> Coroutine[None, None, None] | None:
        return self.middleware.on_start(ctx)

    def on_success(self, ctx: OkContext) -> Coroutine[None, None, None] | None:
        self._overall = 0
        actor_name = f'{ctx.actor.event.name}.{ctx.actor.name}'
        self._per_actor.pop(actor_name, None)
        return self.middleware.on_success(ctx)

    def on_failure(self, ctx: ErrorContext) -> Coroutine[None, None, None] | None:
        actor_name = f'{ctx.actor.event.name}.{ctx.actor.name}'
        if self._overall > self.total_failures:
            return self.middleware.on_failure(ctx)
        if self._per_actor.setdefault(actor_name, 0) > self.actor_failures:
            return self.middleware.on_failure(ctx)
        if ctx.attempts > self.message_failures:
            return self.middleware.on_failure(ctx)
        self._overall += 1
        self._per_actor[actor_name] += 1
        return None


@dataclass(frozen=True)
class FrequencyMiddleware(Middleware):
    """Trigger middleware only once in the given timeframe.

    The on_start and on_success are triggered only once per actor in the given timeframe.
    The on_failure is triggered once per error message per actor in the given timeframe.

    Use it to avoid spamming your notifications channel with many copies of the same
    message when shit hits the fan.

    Args:
        middleware: middleware to trigger.
        timeframe: how long (in seconds) the deduplication window should be.
    """
    middleware: Middleware
    timeframe: float = 600

    _last_trigger_start: dict[str, float] = field(default_factory=dict, init=False)
    _last_trigger_ok: dict[str, float] = field(default_factory=dict, init=False)
    _last_trigger_err: dict[str, float] = field(default_factory=dict, init=False)
    _reported_errors: dict[str, set[type[BaseException]]] = field(
        default_factory=dict,
        init=False,
    )

    def on_start(self, ctx: Context) -> Coroutine[None, None, None] | None:
        actor_name = f'{ctx.actor.event.name}.{ctx.actor.name}'
        now = time.monotonic()
        if now - self._last_trigger_start.get(actor_name, 0) > self.timeframe:
            self._last_trigger_start[actor_name] = now
            return self.middleware.on_start(ctx)
        return None

    def on_success(self, ctx: OkContext) -> Coroutine[None, None, None] | None:
        actor_name = f'{ctx.actor.event.name}.{ctx.actor.name}'
        now = time.monotonic()
        if now - self._last_trigger_ok.get(actor_name, 0) > self.timeframe:
            self._last_trigger_ok[actor_name] = now
            return self.middleware.on_success(ctx)
        return None

    def on_failure(self, ctx: ErrorContext) -> Coroutine[None, None, None] | None:
        actor_name = f'{ctx.actor.event.name}.{ctx.actor.name}'
        now = time.monotonic()
        if now - self._last_trigger_err.get(actor_name, 0) > self.timeframe:
            self._last_trigger_err[actor_name] = now
            err = type(ctx.exception)
            reported_errors = self._reported_errors.setdefault(actor_name, set())
            if err not in reported_errors:
                return self.middleware.on_failure(ctx)
            reported_errors.add(err)
        return None
