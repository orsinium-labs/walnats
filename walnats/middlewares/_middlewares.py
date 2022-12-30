from __future__ import annotations

import logging
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ._base import Middleware


if TYPE_CHECKING:
    from .._context import Context, ErrorContext, OkContext


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
        init=False,
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
            'attempt': ctx.attempts,
        })

    def on_failure(self, ctx: ErrorContext) -> None:
        self.logger.exception('actor failed', extra={
            'actor': ctx.actor.name,
            'event': ctx.actor.event.name,
            'attempt': ctx.attempts,
            'exc': str(ctx.exception),
            'exc_type': type(ctx.exception).__name__,
        })

    def on_success(self, ctx: OkContext) -> None:
        self.logger.debug('event processed', extra={
            'actor': ctx.actor.name,
            'event': ctx.actor.event.name,
            'attempt': ctx.attempts,
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
        attempt = ctx.attempts
        msg = f'event {a.event.name}: received by {a.name}'
        if attempt:
            msg += ' (attempt #{attempt})'
        self.logger.debug(msg)

    def on_failure(self, ctx: ErrorContext) -> None:
        a = ctx.actor
        self.logger.exception(f'event {a.event.name}: actor {a.name} failed')

    def on_success(self, ctx: OkContext) -> None:
        a = ctx.actor
        self.logger.debug(f'event {a.event.name}: processed by {a.name}')
