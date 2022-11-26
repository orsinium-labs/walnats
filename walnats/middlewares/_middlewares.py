from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._base import BaseMiddleware


if TYPE_CHECKING:
    from .._context import Context, ErrorContext, OkContext


@dataclass(frozen=True)
class ExtraLog(BaseMiddleware):
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
