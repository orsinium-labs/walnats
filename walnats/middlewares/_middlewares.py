from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from ._base import Middleware


if TYPE_CHECKING:
    import prometheus_client
    from datadog.dogstatsd import DogStatsd

    from .._context import Context, ErrorContext, OkContext


@dataclass(frozen=True)
class ExtraLogMiddleware(Middleware):
    """Hooks to write logs with ``extra`` fields using ``logging``.

    The ``extra`` fields aren't shown by default, you need to specifically
    configure a logs formatter that supports it. For example, ``python-json-logger``.
    """
    logger: logging.Logger | logging.LoggerAdapter = logging.getLogger(__package__)

    def on_start(self, ctx: Context) -> None:
        self.logger.debug('event received', extra=dict(
            actor=ctx.actor.name,
            event=ctx.actor.event.name,
            attempt=ctx.metadata.num_delivered,
        ))

    def on_failure(self, ctx: ErrorContext) -> None:
        self.logger.exception('actor failed', extra=dict(
            actor=ctx.actor.name,
            event=ctx.actor.event.name,
            attempt=ctx.metadata.num_delivered,
            exc=str(ctx.exception),
            exc_type=type(ctx.exception).__name__,
        ))

    def on_success(self, ctx: OkContext) -> None:
        self.logger.debug('event processed', extra=dict(
            actor=ctx.actor.name,
            event=ctx.actor.event.name,
            attempt=ctx.metadata.num_delivered,
            duration=ctx.duration,
        ))


@dataclass(frozen=True)
class StatsdMiddleware(Middleware):
    """Hooks to emit statsd metrics using Datadog statsd client.

    We use Datadog statsd client because it is (compared to all alternatives)
    well maintained, type safe, and supports tags.
    """
    client: DogStatsd

    def on_start(self, ctx: Context) -> None:
        self.client.increment(
            f'walnats.{ctx.actor.event.name}.{ctx.actor.name}.started',
        )

    def on_failure(self, ctx: ErrorContext) -> None:
        self.client.increment(
            f'walnats.{ctx.actor.event.name}.{ctx.actor.name}.failed',
        )

    def on_success(self, ctx: OkContext) -> None:
        self.client.increment(
            f'walnats.{ctx.actor.event.name}.{ctx.actor.name}.processed',
        )
        self.client.histogram(
            f'walnats.{ctx.actor.event.name}.{ctx.actor.name}.duration',
            ctx.duration,
        )


@lru_cache(maxsize=256)
def _get_prometheus_counter(name: str, descr: str) -> prometheus_client.Counter:
    return prometheus_client.Counter(name=name, documentation=descr)


@lru_cache(maxsize=256)
def _get_prometheus_histogram(name: str, descr: str) -> prometheus_client.Histogram:
    return prometheus_client.Histogram(name=name, documentation=descr)


@dataclass(frozen=True)
class PrometheusMiddleware(Middleware):
    """Hooks to emit prometheus metrics.
    """

    def on_start(self, ctx: Context) -> None:
        _get_prometheus_counter(
            name=f'walnats.{ctx.actor.event.name}.{ctx.actor.name}.started',
            documentation='How many times handler was called',
        ).inc()

    def on_failure(self, ctx: ErrorContext) -> None:
        _get_prometheus_counter(
            name=f'walnats.{ctx.actor.event.name}.{ctx.actor.name}.failed',
            documentation='How many times handler failed',
        ).inc()

    def on_success(self, ctx: OkContext) -> None:
        _get_prometheus_counter(
            name=f'walnats.{ctx.actor.event.name}.{ctx.actor.name}.processed',
            documentation='How many messages handler processed',
        ).inc()
        _get_prometheus_histogram(
            name=f'walnats.{ctx.actor.event.name}.{ctx.actor.name}.duration',
            documentation='How long it took for handler to process message',
        ).observe(ctx.duration)
