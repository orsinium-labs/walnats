
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

import nats.js
from nats.aio.msg import Msg

from ._event import Event
from ._serializers import Model
from ._error_handling import ErrorContext, ErrorHandler, log_error

M = TypeVar('M', bound=Model)


@dataclass(frozen=True)
class Actor(Generic[M]):
    name: str
    event: Event[M]
    handler: Callable[[M], Awaitable[None]]
    ack_wait: float | None = None
    max_attempts: int | None = None
    on_failure: ErrorHandler[M] = log_error

    @property
    def consumer_name(self) -> str:
        assert self.name
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
        """Add Nats consumer.

        After this is executed for the first time, the stream will start collecting
        all messages for the actor.
        """
        await js.add_consumer(
            stream=self.event.stream_name,
            config=self._consumer_config,
        )

    async def _listen(
        self, *,
        js: nats.js.JetStreamContext,
        poll_sem: asyncio.Semaphore,
        worker_sem: asyncio.Semaphore,
        poll_delay: float,
        burst: bool,
        batch: int,
    ) -> None:
        """Subscribe to the stream, pull relevant messages, and run the handler for each.

        See SubConnection.listen for the list of arguments.
        """
        psub = await js.pull_subscribe_bind(
            durable=self.consumer_name,
            stream=self.event.stream_name,
        )
        try:
            while True:
                await self._pull_and_handle(
                    poll_sem=poll_sem,
                    worker_sem=worker_sem,
                    poll_delay=poll_delay,
                    batch=batch,
                    psub=psub,
                )
                if burst:
                    return
        finally:
            await psub.unsubscribe()

    async def _pull_and_handle(
        self, *,
        poll_sem: asyncio.Semaphore,
        worker_sem: asyncio.Semaphore,
        poll_delay: float,
        batch: int,
        psub: nats.js.JetStreamContext.PullSubscription,
    ) -> None:
        # don't try polling new messages if there are no workers to handle them
        if worker_sem.locked():
            await worker_sem.acquire()
            worker_sem.release()

        # poll messages
        async with poll_sem:
            try:
                msgs = await psub.fetch(batch=batch, timeout=poll_delay)
            except asyncio.TimeoutError:
                return

        # run workers
        tasks: list[asyncio.Task] = []
        for msg in msgs:
            coro = self._handle_message(msg, worker_sem)
            task = asyncio.create_task(coro)
            tasks.append(task)
        try:
            await asyncio.gather(*tasks)
        except (Exception, asyncio.CancelledError):
            for task in tasks:
                task.cancel()

    async def _handle_message(self, msg: Msg, sem: asyncio.Semaphore) -> None:
        pulse_task = asyncio.create_task(self._pulse(msg))
        message = None
        try:
            async with sem:
                message = self.event.serializer.decode(msg.data)
                await self.handler(message)
        except (Exception, asyncio.CancelledError):
            pulse_task.cancel()
            await msg.nak()
            await self.on_failure(ErrorContext(actor=self, message=message))
        else:
            pulse_task.cancel()
            await msg.ack_sync()

    async def _pulse(self, msg: Msg) -> None:
        """Keep notifying nats server that the message handling is in progress.
        """
        if self.ack_wait is None:
            return
        while True:
            await msg.in_progress()
