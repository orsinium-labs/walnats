from __future__ import annotations

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING

from ._base import Middleware


if TYPE_CHECKING:
    import aiozipkin
    import opentelemetry.trace
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
    _span: ContextVar[aiozipkin.SpanAbc | None] = field(
        default_factory=lambda: ContextVar('span', default=None),
        init=False,
    )

    @property
    def span(self) -> aiozipkin.SpanAbc | None:
        """The current span. Use it from handler to create child spans.

        May be ``None`` if you forgot to add the middleware for the actor,
        and so ``on_start`` hasn't been called.
        """
        return self._span.get()

    def on_start(self, ctx: Context) -> None:
        trace_ctx = self.tracer._next_context(sampled=self.sampled)
        if ctx.trace_id is not None:
            trace_ctx = trace_ctx._replace(trace_id=ctx.trace_id)
        span = self.tracer.to_span(trace_ctx)
        span.name(ctx.actor.name)
        span.tag('event', ctx.actor.event.name)
        span.kind('CONSUMER')
        span.start()
        self._span.set(span)

    def on_failure(self, ctx: ErrorContext) -> None:
        span = self._span.get()
        if span is not None:
            span.finish(exception=ctx.exception)  # type: ignore[arg-type]

    def on_success(self, ctx: OkContext) -> None:
        span = self._span.get()
        assert span is not None
        span.finish()


@dataclass(frozen=True)
class OpenTelemetryTraceMiddleware(Middleware):
    tracer: opentelemetry.trace.Tracer
    _span: ContextVar[opentelemetry.trace.Span | None] = field(
        default_factory=lambda: ContextVar('span', default=None),
        init=False,
    )

    @property
    def span(self) -> opentelemetry.trace.Span | None:
        """The current span. Use it from handler to create child spans.

        May be ``None`` if you forgot to add the middleware for the actor,
        and so ``on_start`` hasn't been called.
        """
        return self._span.get()

    def on_start(self, ctx: Context) -> None:
        import opentelemetry.trace
        from opentelemetry.trace.propagation import tracecontext

        trace_context: opentelemetry.trace.Context | None = None
        if ctx.trace_id is not None:
            trace_context = tracecontext.TraceContextTextMapPropagator().extract(
                carrier={'traceparent': ctx.trace_id},
            )
        span = self.tracer.start_span(
            name=ctx.actor.name,
            kind=opentelemetry.trace.SpanKind.CONSUMER,
            attributes={'event': ctx.actor.event.name},
            context=trace_context,
        )
        self._span.set(span)

    def on_failure(self, ctx: ErrorContext) -> None:
        span = self._span.get()
        if span is not None:
            if not isinstance(ctx.exception, asyncio.CancelledError):
                span.record_exception(ctx.exception)
            span.end()

    def on_success(self, ctx: OkContext) -> None:
        span = self._span.get()
        assert span is not None
        span.end()
