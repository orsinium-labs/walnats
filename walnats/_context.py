from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from ._constants import HEADER_DELAY, HEADER_TRACE


if TYPE_CHECKING:
    import asyncio

    from nats.aio.msg import Msg

    from ._actors import Actor


@dataclass(frozen=True)
class BaseContext:

    actor: Actor
    """
    Actor object from which the callback is triggered.
    The most common things you want from it are ``ctx.actor.name``
    and ``ctx.actor.event.name``.
    """

    _msg: Msg

    @cached_property
    def metadata(self) -> Msg.Metadata:
        """Message metadata provided by Nats.
        """
        return self._msg.metadata

    @cached_property
    def seq_number(self) -> int:
        """Sequence ID of the message in Nats JetStream.
        """
        seq = self.metadata.sequence
        return seq.stream if seq else 0

    @cached_property
    def attempts(self) -> int:
        """The number of times the message was tried to be delivered.

        1 if this is the first delivery. Always positive.

        It is possible that there already were delivery attempts but the handler
        wasn't triggered. For instance, if nats.py client lost the message because of
        a bug or message body deserialization has failed.
        So, the number of delivery attempts might be higher than the number of
        times the handler was triggered for the message.
        """
        attempts = self.metadata.num_delivered or 1
        if attempts >= 2:
            delayed = (self._msg.headers or {}).get(HEADER_DELAY)
            if delayed:
                return attempts - 1
        return attempts

    @cached_property
    def trace_id(self) -> str | None:
        """The ``trace_id`` provided when emitting the message.

        This value is typically used for distributed tracing.
        """
        if self._msg.headers is None:
            return None
        return self._msg.headers.get(HEADER_TRACE)


@dataclass(frozen=True)
class Context(BaseContext):
    """Context passed into :meth:`walnats.middlewares.Middleware.on_start` callback.
    """

    message: object
    """
    Decoded message payload.
    """


@dataclass(frozen=True)
class ErrorContext(BaseContext):
    """Context passed into :class:`walnats.middlewares.Middleware.on_failure` callback.
    """

    message: object | None
    """
    Decoded message payload. Will be None if the failure is raise while trying
    to decode the message payload.
    """

    exception: Exception | asyncio.CancelledError
    """The exception raised.
    """


@dataclass(frozen=True)
class OkContext(BaseContext):
    """Context passed into :meth:`walnats.middlewares.Middleware.on_success` callback.
    """

    message: object
    """
    Decoded message payload.
    """

    duration: float
    """
    How long it took for handler to finish the job. It also includes time spent in
    ``await``, so be mindful of it when using it to reason about handler performance.
    """
