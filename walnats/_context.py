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
    exception: Exception | asyncio.CancelledError


@dataclass(frozen=True)
class OkContext(Context):
    duration: float
