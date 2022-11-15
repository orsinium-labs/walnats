from __future__ import annotations
import asyncio
from dataclasses import dataclass
from functools import cached_property
from typing import Generic, TypeVar

import nats
import nats.js

from ._serializers import Serializer, get_serializer, Model

M = TypeVar('M', bound='Model')


@dataclass(frozen=True)
class Limits:
    """Stream configuration options limiting the Stream size.

    https://docs.nats.io/nats-concepts/jetstream/streams#configuration
    """
    # Maximum age of any message in the Stream.
    age: float | None = None
    # How many Consumers can be defined for a given Stream.
    consumers: int | None = None
    # How many messages may be in a Stream.
    messages: int | None = None
    # How many bytes the Stream may contain.
    bytes: int | None = None
    # The largest message that will be accepted by the Stream.
    message_size: int | None = None


@dataclass(frozen=True)
class Event(Generic[M]):
    name: str
    model: type[M]
    serializer: Serializer[M] | None = None
    description: str | None = None
    limits: Limits = Limits()

    @property
    def subject_name(self) -> str:
        return self.name

    @property
    def stream_name(self) -> str:
        return self.name

    @cached_property
    def _serializer(self) -> Serializer[M]:
        if self.serializer is None:
            return get_serializer(self.model)
        return self.serializer

    @property
    def _stream_config(self) -> nats.js.api.StreamConfig:
        """
        https://docs.nats.io/nats-concepts/jetstream/streams#configuration
        """
        return nats.js.api.StreamConfig(
            name=self.stream_name,
            subjects=[self.subject_name],
            description=self.description,
            retention=nats.js.api.RetentionPolicy.INTEREST,

            # limits
            max_age=self.limits.age,
            max_consumers=self.limits.consumers,
            max_msgs=self.limits.messages,
            max_bytes=self.limits.bytes,
            max_msg_size=self.limits.message_size,
        )

    async def _add(self, js: nats.js.JetStreamContext) -> None:
        await js.add_stream(self._stream_config)

    async def _monitor(self, nc: nats.NATS, q: asyncio.Queue[M]) -> None:
        sub = await nc.subscribe('count')
        async for msg in sub.messages:
            event = self._serializer.decode(msg.data)
            await q.put(event)
