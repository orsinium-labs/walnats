from __future__ import annotations

import asyncio
import dataclasses
from functools import cached_property
from typing import Generic, TypeVar

import nats
import nats.js
import nats.js.errors

from .._errors import convert_stream_errors
from ..serializers import Serializer, get_serializer
from ._limits import Limits


T = TypeVar('T')
R = TypeVar('R')


@dataclasses.dataclass(frozen=True)
class BaseEvent(Generic[T, R]):
    """
    Internal-only class to provide shared behavior for different kinds of events.
    Use :class:`walnats.Event` and its methods to create an event.
    """

    name: str
    """
    The event name, used for stream and subject names in Nats.
    Choose carefully, you cannot ever change it.
    """

    schema: type[T]
    """
    Python type of the data transmitted. For example, dict, pydantic model,
    dataclass, protobuf message, etc.
    """

    serializer: Serializer[T] | None = None
    """
    Serializer instance that can turn a schema instance into bytes and back again.
    By default, a serializer from the built-in ones will be picked.
    In most of the cases, it will produce JSON.
    """

    description: str | None = None
    """
    Event description, will be shown in stream description in Nats.
    """

    limits: Limits = Limits()
    """
    Limits for messages in the Nats stream (like size, age, number).
    """

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
        assert 0 < len(self.name) <= 255
        return self.name.replace('.', '-')

    def encode(self, msg: T) -> bytes:
        """Convert an event payload into bytes.

        Used by Events.emit to transfer events over the network.
        """
        return self._serializer.encode(msg)

    def decode(self, data: bytes) -> T:
        """Convert raw bytes from event payload into a Python type.

        Used by Actor to extract the event message from Nats message payload.
        """
        return self._serializer.decode(data)

    @cached_property
    def _serializer(self) -> Serializer:
        if self.serializer is not None:
            return self.serializer
        return get_serializer(self.schema)

    @property
    def _stream_config(self) -> nats.js.api.StreamConfig:
        """Configuration for Nats JetStream stream.

        https://docs.nats.io/nats-concepts/jetstream/streams#configuration
        """
        assert self.description is None or len(self.description) <= 4 * 1024
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

    async def _sync(
        self,
        js: nats.js.JetStreamContext,
        create: bool,
        update: bool,
    ) -> None:
        """Add Nats JetStream stream.

        Must be called before any actors can be registered.
        """
        if create:
            with convert_stream_errors(exists_ok=update):
                await js.add_stream(self._stream_config)
                return
        if update:
            with convert_stream_errors():
                await js.update_stream(self._stream_config)

    async def _monitor(self, nc: nats.NATS, queue: asyncio.Queue[T]) -> None:
        """Subscribe to the subject and emit all events into the given queue.
        """
        sub = await nc.subscribe(self.subject_name)
        print(sub)
        async for msg in sub.messages:
            event = self.decode(msg.data)
            await queue.put(event)


@dataclasses.dataclass(frozen=True)
class EventWithResponse(BaseEvent[T, R]):
    response_schema: type[R] = ...  # type: ignore[assignment]
    response_serializer: Serializer[R] | None = None

    def encode_response(self, msg: R) -> bytes:
        """Convert response payload into bytes.

        Used by :class:`walnats.Actor` to transfer the response over the network.
        """
        return self._response_serializer.encode(msg)

    def decode_response(self, data: bytes) -> R:
        """Convert raw bytes from event payload into a Python type.

        Used by :class:`walnats.types.ConnectedEvents.request` to extract
        the response from Nats JetStream message payload.
        """
        return self._response_serializer.decode(data)

    @cached_property
    def _response_serializer(self) -> Serializer:
        if self.response_serializer is not None:
            return self.response_serializer
        return get_serializer(self.response_schema)


class Event(BaseEvent[T, None]):
    """Container for information about event: stream config, schema, serializer.

    ::

        USER_CREATED = walnats.Event('user-created', User)
    """

    def with_response(
        self,
        schema: type[R],
        serializer: Serializer[R] | None = None,
    ) -> EventWithResponse[T, R]:
        """
        Create a copy of the Event that can be used with
        :meth:`walnats.types.ConnectedEvents.request`.

        The same copy must be used with the :class:`walnats.Actor`.
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
