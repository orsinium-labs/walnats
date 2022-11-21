from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import cached_property
from typing import Generic, TypeVar

import nats
import nats.js

from ..serializers import Serializer, get_serializer


T = TypeVar('T')
R = TypeVar('R')


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


class BaseEvent(Generic[T, R]):

    def __init__(
        self,
        name: str,
        schema: type[T],
        *,
        serializer: Serializer[T] | None = None,
        description: str | None = None,
        limits: Limits = Limits(),
    ) -> None:
        assert name
        self._name = name
        self._schema = schema
        self._description = description
        self._limits = limits
        if serializer is not None:
            self.serializer = serializer

    @property
    def subject_name(self) -> str:
        return self._name

    @property
    def stream_name(self) -> str:
        return self._name

    @cached_property
    def serializer(self) -> Serializer[T]:
        return get_serializer(self._schema)

    @property
    def _stream_config(self) -> nats.js.api.StreamConfig:
        """
        https://docs.nats.io/nats-concepts/jetstream/streams#configuration
        """
        return nats.js.api.StreamConfig(
            name=self.stream_name,
            subjects=[self.subject_name],
            description=self._description,
            retention=nats.js.api.RetentionPolicy.INTEREST,

            # limits
            max_age=self._limits.age,
            max_consumers=self._limits.consumers,
            max_msgs=self._limits.messages,
            max_bytes=self._limits.bytes,
            max_msg_size=self._limits.message_size,
        )

    async def _add(self, js: nats.js.JetStreamContext) -> None:
        await js.add_stream(self._stream_config)

    async def _monitor(self, nc: nats.NATS, q: asyncio.Queue[T]) -> None:
        sub = await nc.subscribe('count')
        async for msg in sub.messages:
            event = self.serializer.decode(msg.data)
            await q.put(event)

    def __repr__(self) -> str:
        return f'{type(self).__name__}({repr(self._name)}, ...)'


class EventWithResponse(BaseEvent[T, R]):
    def __init__(
        self,
        response_schema: type[R],
        response_serializer: Serializer[R] | None,
        **kwargs,
    ) -> None:
        self._response_schema = response_schema
        if response_serializer is not None:
            self.response_serializer = response_serializer
        super().__init__(**kwargs)

    @cached_property
    def response_serializer(self) -> Serializer[R]:
        return get_serializer(self._response_schema)


class Event(BaseEvent[T, None]):
    def with_response(
        self,
        schema: type[R],
        serializer: Serializer[R] | None = None,
    ) -> EventWithResponse[T, R]:
        return EventWithResponse(
            response_schema=schema,
            response_serializer=serializer,
            name=self._name,
            schema=self._schema,
            description=self._description,
            limits=self._limits,
            serializer=self.serializer,
        )
