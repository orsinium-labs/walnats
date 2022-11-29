from __future__ import annotations

import asyncio
import dataclasses
from typing import Generic, TypeVar

import nats
import nats.js

from ..serializers import Serializer, get_serializer


T = TypeVar('T')
R = TypeVar('R')


@dataclasses.dataclass(frozen=True)
class Limits:
    """Stream configuration options limiting the Stream size.

    Args:
        age: Maximum age of any message in the Stream in seconds.
        consumers: How many Consumers can be defined for a given Stream.
        messages: How many messages may be in a Stream.
        bytes: How many bytes the Stream may contain.
        message_size: The largest message that will be accepted by the Stream.

    https://docs.nats.io/nats-concepts/jetstream/streams#configuration
    """
    age: float | None = None
    consumers: int | None = None
    messages: int | None = None
    bytes: int | None = None
    message_size: int | None = None

    def evolve(self, **kwargs: float | None) -> Limits:
        """Create a copy of Limits with the given fields changed.
        """
        return dataclasses.replace(self, **kwargs)


@dataclasses.dataclass
class BaseEvent(Generic[T, R]):
    """Internal-only class to provide shared behavior for Event and EventWithResponse.
    """
    name: str
    schema: type[T]
    serializer: Serializer[T] | None = None
    description: str | None = None
    limits: Limits = Limits()

    @property
    def subject_name(self) -> str:
        """The name of Nats subject used to emit messages.
        """
        return self.name

    @property
    def stream_name(self) -> str:
        """The name of Nats JetStream stream used to provide message persistency.

        Walnats makes exactly one stream per subject.
        """
        return self.name

    def encode(self, msg: T) -> bytes:
        """Convert an event payload into bytes.

        Used by Events.emit to transfer events over the network.
        """
        if self.serializer is None:
            self.serializer = get_serializer(self.schema)
        return self.serializer.encode(msg)

    def decode(self, data: bytes) -> T:
        """Convert raw bytes from event payload into a Python type.

        Used by Actor to extract the event message from Nats message payload.
        """
        if self.serializer is None:
            self.serializer = get_serializer(self.schema)
        return self.serializer.decode(data)

    @property
    def _stream_config(self) -> nats.js.api.StreamConfig:
        """Configuration for Nats JetStream stream.

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
        """Add Nats JetStream stream.

        Must be called before any actors can be registered.
        """
        await js.add_stream(self._stream_config)

    async def _monitor(self, nc: nats.NATS, queue: asyncio.Queue[T]) -> None:
        """Subscribe to the subject and emit all events into the given queue.
        """
        sub = await nc.subscribe(self.subject_name)
        print(sub)
        async for msg in sub.messages:
            event = self.decode(msg.data)
            await queue.put(event)


@dataclasses.dataclass
class EventWithResponse(BaseEvent[T, R]):
    response_schema: type[R] = ...  # type: ignore[assignment]
    response_serializer: Serializer[R] | None = None

    def encode_response(self, msg: R) -> bytes:
        if self.response_serializer is None:
            self.response_serializer = get_serializer(self.response_schema)
        return self.response_serializer.encode(msg)

    def decode_response(self, data: bytes) -> R:
        if self.response_serializer is None:
            self.response_serializer = get_serializer(self.response_schema)
        return self.response_serializer.decode(data)


class Event(BaseEvent[T, None]):
    """Container for information about event: stream config, schema, serializer.

    Args:
        schema: Python type of the data transmitted. For example, dict, pydantic
            model, dataclass, protobuf message, etc.
        name: The event name, used for stream and subject names in Nats.
            Choose carefully, you cannot ever change it.
        serializer: Serializer instance that can turn a schema instance into bytes and
            back again. By default, a serializer from the built-in ones will be picked.
            In most of the cases, it will produce JSON.
        description: Event description, will be shown in stream description in Nats.
        limits: Limits for messages in the Nats stream: size, age, number.
    """

    def with_response(
        self,
        schema: type[R],
        serializer: Serializer[R] | None = None,
    ) -> EventWithResponse[T, R]:
        """Create a copy of the Event that can be used with ConnectedEvents.request.

        The same copy must be used with the Actor.
        Otherwise, the response won't be emitted.
        """
        return EventWithResponse(
            response_schema=schema,
            response_serializer=serializer,
            name=self.name,
            schema=self.schema,
            description=self.description,
            limits=self.limits,
            serializer=self.serializer,
        )
