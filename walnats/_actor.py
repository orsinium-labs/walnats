
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

from nats.aio.msg import Msg
import nats.js

from ._event import Model, Event


M = TypeVar('M', bound=Model)


@dataclass(frozen=True)
class Actor(Generic[M]):
    name: str
    event: Event[M]
    handler: Callable[[M], Awaitable[None]]
    ack_wait: float | None = None

    @property
    def consumer_name(self) -> str:
        return self.name

    @property
    def _consumer_config(self) -> nats.js.api.ConsumerConfig:
        return nats.js.api.ConsumerConfig(
            durable_name=self.consumer_name,
            ack_wait=self.ack_wait,
        )

    async def _add(self, js: nats.js.JetStreamContext) -> None:
        await js.add_consumer(
            stream=self.event.stream_name,
            config=self._consumer_config,
        )

    async def _listen(self, js: nats.js.JetStreamContext) -> None:
        psub = await js.pull_subscribe_bind(
            durable=self.consumer_name,
            stream=self.event.stream_name,
        )
        while True:
            try:
                msgs = await psub.fetch(timeout=5)
            except asyncio.TimeoutError:
                continue
            for msg in msgs:
                event = self.event.model.parse_raw(msg.data.decode())
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
