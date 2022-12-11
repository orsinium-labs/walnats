from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import asyncio

    from nats.aio.msg import Msg

    from ._actors import Actor


@dataclass(frozen=True)
class Context:
    """Base context, passed into :meth:`walnats.middlewares.Middleware.on_start` callback.

    Args:
        actor: Actor object from which the callback is triggered.
            The most common things you want from it are ``ctx.actor.name``
            and ``ctx.actor.event.name``.
        message: decoded message payload.
    """
    actor: Actor
    message: object | None
    _msg: Msg

    @cached_property
    def metadata(self) -> Msg.Metadata:
        return self._msg.metadata

    @cached_property
    def seq_number(self) -> int:
        """Sequence ID of the message in Nats JetStream.
        """
        seq = self.metadata.sequence
        return seq.stream if seq else 0

    @property
    def is_first_attempt(self) -> bool:
        """Check if this is the first attempt to handle the message.
        """
        return self.metadata.num_delivered == 0


@dataclass(frozen=True)
class ErrorContext(Context):
    """Context passed into :class:`walnats.middlewares.Middleware.on_failure` callback.

    Args:
        exception: the raised exception.

    The ``message`` will be None if the error occured while trying to decode the message.
    """
    exception: Exception | asyncio.CancelledError


@dataclass(frozen=True)
class OkContext(Context):
    """Context passed into :meth:`walnats.middlewares.Middleware.on_success` callback.

    Args:
        duration: how long it took for handler to finish the job.
            It also includes time spent in ``await``, so be mindful of it
            when using it to reason about handler performance.
    """
    duration: float
