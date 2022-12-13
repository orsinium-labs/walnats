from __future__ import annotations

import logging
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING

from ._base import Middleware


if TYPE_CHECKING:
    import aiozipkin
    from datadog.dogstatsd import DogStatsd
    from prometheus_client import Counter, Histogram

    from .._context import Context, ErrorContext, OkContext


try:
    import prometheus_client
except ImportError:
    prometheus_client = None  # type: ignore[assignment]

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None  # type: ignore[assignment]


@dataclass(frozen=True)
class CurrentContextMiddleware(Middleware):
    """Middleware that records the current context on start.

    This is a small trick to make the context available from handler or decorators
    when you need additional information about the Nats message received.
    We don't pass context in handlers explicitly by default because most of the handlers
    should care only about the actual message payload,
    independent of how it was delivered.
    """
    _context: ContextVar[Context] = field(
        default_factory=lambda: ContextVar('context'),
    )

    @property
    def context(self) -> Context:
        """The context for the currently running job.
        """
        return self._context.get()

    def on_start(self, ctx: Context) -> None:
        self._context.set(ctx)


@dataclass(frozen=True)
class ExtraLogMiddleware(Middleware):
    """Write logs with ``extra`` fields using ``logging``.

    The ``extra`` fields aren't shown by default, you need to specifically
    configure a logs formatter that supports it. For example, ``python-json-logger``.
    """
    logger: logging.Logger | logging.LoggerAdapter = logging.getLogger(__package__)

    def on_start(self, ctx: Context) -> None:
        self.logger.debug('event received', extra={
            'actor': ctx.actor.name,
            'event': ctx.actor.event.name,
            'attempt': ctx.metadata.num_delivered,
        })

    def on_failure(self, ctx: ErrorContext) -> None:
        self.logger.exception('actor failed', extra={
            'actor': ctx.actor.name,
            'event': ctx.actor.event.name,
            'attempt': ctx.metadata.num_delivered,
            'exc': str(ctx.exception),
            'exc_type': type(ctx.exception).__name__,
        })

    def on_success(self, ctx: OkContext) -> None:
        self.logger.debug('event processed', extra={
            'actor': ctx.actor.name,
            'event': ctx.actor.event.name,
            'attempt': ctx.metadata.num_delivered,
            'duration': ctx.duration,
        })


@dataclass(frozen=True)
class TextLogMiddleware(Middleware):
    """Write plain text logs using ``logging``.

    The middleware might be useful for debugging. For the prod, consider using
    :class:`walnats.middlewares.ExtraLogMiddleware`.

    By default, DEBUG-level logs are not shown. You need to enable them explicitly::

        import logging
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

    """
    logger: logging.Logger | logging.LoggerAdapter = logging.getLogger(__package__)

    def on_start(self, ctx: Context) -> None:
        a = ctx.actor
        attempt = ctx.metadata.num_delivered
        msg = f'event {a.event.name}: received by {a.name}'
        if attempt and attempt > 1:
            msg += ' (attempt #{attempt})'
        self.logger.debug(msg)

    def on_failure(self, ctx: ErrorContext) -> None:
        a = ctx.actor
        self.logger.exception(f'event {a.event.name}: actor {a.name} failed')

    def on_success(self, ctx: OkContext) -> None:
        a = ctx.actor
        self.logger.debug(f'event {a.event.name}: processed by {a.name}')


@dataclass(frozen=True)
class StatsdMiddleware(Middleware):
    """Emit statsd metrics using Datadog statsd client.

    We use Datadog statsd client because it is (compared to all alternatives)
    well maintained, type safe, and supports tags.

    Requires `datadog <https://github.com/DataDog/datadogpy>`_ package to be installed.
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
def _get_prometheus_counter(name: str, descr: str) -> Counter:
    if prometheus_client is None:
        raise ImportError('prometheus-client is not installed')
    return prometheus_client.Counter(
        name=name,
        documentation=descr,
        labelnames=['event', 'agent'],
    )


@lru_cache(maxsize=256)
def _get_prometheus_histogram(name: str, descr: str) -> Histogram:
    if prometheus_client is None:
        raise ImportError('prometheus-client is not installed')
    return prometheus_client.Histogram(
        name=name,
        documentation=descr,
        labelnames=['event', 'agent'],
    )


@dataclass(frozen=True)
class PrometheusMiddleware(Middleware):
    """Store Prometheus metrics.

    Requires `prometheus-client <https://github.com/prometheus/client_python>`_
    package to be installed.
    """

    def on_start(self, ctx: Context) -> None:
        _get_prometheus_counter(
            name='walnats_handler_started',
            descr='How many times handler was called',
        ).labels(ctx.actor.event.name, ctx.actor.name).inc()

    def on_failure(self, ctx: ErrorContext) -> None:
        _get_prometheus_counter(
            name='walnats_handler_failed',
            descr='How many times handler failed',
        ).labels(ctx.actor.event.name, ctx.actor.name).inc()

    def on_success(self, ctx: OkContext) -> None:
        _get_prometheus_counter(
            name='walnats_handler_succeeded',
            descr='How many messages handler processed',
        ).labels(ctx.actor.event.name, ctx.actor.name).inc()
        _get_prometheus_histogram(
            name='walnats_handler_duration',
            descr='How long it took for handler to process message',
        ).labels(ctx.actor.event.name, ctx.actor.name).observe(ctx.duration)


class SentryMiddleware(Middleware):
    """Report actor failures into Sentry using the official Sentry SDK.

    The failure report will include tags:

    * actor: actor name.
    * event: event name.

    Also, the "additional data" section will have:

    * delivered_at: timestamp when Nats delivered the message to the consumer.
    * stream_seq_id: sequence ID of the message in the Nats JetStream stream.

    Requires `sentry-sdk <https://github.com/getsentry/sentry-python>`_
    package to be installed.
    """
    __slots__ = ()

    def __init__(self) -> None:
        from sentry_sdk.integrations.logging import ignore_logger

        # disable capturing log message about actor failure
        ignore_logger('walnats.actor')

    # TODO(@orsinium): Can we have a task-local Sentry scope?
    # sentry_sdk.Hub is thread-local.
    # Example of making a scope:
    # https://github.com/jacobsvante/sentry-dramatiq/

    def on_failure(self, ctx: ErrorContext) -> None:
        # shouldn't fail because we import from sentry_sdk in __init__
        assert sentry_sdk is not None, 'sentry-sdk is not installed'
        sentry_sdk.capture_exception(
            error=ctx.exception,
            tags={
                'actor': ctx.actor.name,
                'event': ctx.actor.event.name,
            },
            extras={
                'stream_seq_id': ctx.seq_number,
                'delivered_at': str(ctx.metadata.timestamp),
            },
        )


@dataclass(frozen=True)
class ZipkinMiddleware(Middleware):
    """Emit Zipkin span.

    Requires `aiozipkin <https://github.com/aio-libs/aiozipkin>`_ package to be installed.
    """
    tracer: aiozipkin.Tracer
    sampled: bool | None = None
    _spans: dict[int, aiozipkin.SpanAbc] = field(default_factory=dict)

    def on_start(self, ctx: Context) -> None:
        span = self.tracer.new_trace(sampled=self.sampled)
        span.name(ctx.actor.name)
        span.tag('event', ctx.actor.event.name)
        span.kind('CONSUMER')
        span.annotate
        span.start()
        self._spans[ctx.seq_number] = span

    def on_failure(self, ctx: ErrorContext) -> None:
        span = self._spans.get(ctx.seq_number)
        if span is not None:
            span.finish(exception=ctx.exception)  # type: ignore[arg-type]

    def on_success(self, ctx: OkContext) -> None:
        span = self._spans[ctx.seq_number]
        span.finish()
