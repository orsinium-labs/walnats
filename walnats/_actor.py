
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

import nats.js
from nats.aio.msg import Msg

from ._event import Event
from ._serializers import Model

M = TypeVar('M', bound=Model)


@dataclass(frozen=True)
class Actor(Generic[M]):
    name: str
    event: Event[M]
    handler: Callable[[M], Awaitable[None]]
    ack_wait: float | None = None
    max_attempts: int | None = None

    @property
    def consumer_name(self) -> str:
        return self.name

    @property
    def _consumer_config(self) -> nats.js.api.ConsumerConfig:
        """
        https://docs.nats.io/nats-concepts/jetstream/consumers#configuration
        """
        return nats.js.api.ConsumerConfig(
            durable_name=self.consumer_name,
            ack_wait=self.ack_wait,
            max_deliver=self.max_attempts,
        )

    async def _add(self, js: nats.js.JetStreamContext) -> None:
        await js.add_consumer(
            stream=self.event.stream_name,
            config=self._consumer_config,
        )

    async def _listen(
        self,
        js: nats.js.JetStreamContext,
        sem: asyncio.Semaphore,
        stop_after: int,
    ) -> None:
        psub = await js.pull_subscribe_bind(
            durable=self.consumer_name,
            stream=self.event.stream_name,
        )
        total_consumed = 0
        while True:
            async with sem:
                try:
                    msgs = await psub.fetch(timeout=5)
                except asyncio.TimeoutError:
                    continue
                for msg in msgs:
                    await self._handle_message(msg)
                if stop_after:
                    total_consumed += len(msgs)
                    if total_consumed >= stop_after:
                        return

    async def _handle_message(self, msg: Msg) -> None:
        event = self.event.serializer.decode(msg.data)
        pulse_task = asyncio.create_task(self._pulse(msg))
        try:
            await self.handler(event)
        except (Exception, asyncio.CancelledError):
            pulse_task.cancel()
            await msg.nak()
            raise
        pulse_task.cancel()
        await msg.ack_sync()

    @staticmethod
    async def _pulse(msg: Msg) -> None:
        while True:
            await msg.in_progress()
