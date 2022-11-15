from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

import nats
import nats.js
import pydantic
pydantic.BaseModel

M = TypeVar('M', bound='Model')


class Model(Protocol):
    def json(self) -> str:
        raise NotImplementedError

    @classmethod
    def parse_raw(cls: type[M], data: str) -> M:
        raise NotImplementedError


@dataclass(frozen=True)
class Event(Generic[M]):
    name: str
    model: type[M]
    max_age: float | None = None

    @property
    def subject_name(self) -> str:
        return self.name

    @property
    def stream_name(self) -> str:
        return self.name

    @property
    def _stream_config(self) -> nats.js.api.StreamConfig:
        return nats.js.api.StreamConfig(
            name=self.stream_name,
            max_age=self.max_age,
        )

    async def _add(self, js: nats.js.JetStreamContext) -> None:
        await js.add_stream(self._stream_config)

    async def _monitor(self, nc: nats.NATS, q: asyncio.Queue[M]) -> None:
        sub = await nc.subscribe('count')
        async for msg in sub.messages:
            event = self.model.parse_raw(msg.data.decode())
            await q.put(event)
