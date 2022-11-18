
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from logging import getLogger
from time import perf_counter
from typing import Awaitable, Callable, Generic, TypeVar

import nats.js
from nats.aio.msg import Msg

from ._event import Event
from ._serializers import Model
from ._context import ErrorContext, Context, OkContext
from .middlewares import BaseAsyncMiddleware, BaseSyncMiddleware
from ._tasks import Tasks

M = TypeVar('M', bound=Model)
logger = getLogger(__package__)


@dataclass(frozen=True)
class Actor(Generic[M]):
    name: str
    event: Event[M]
    handler: Callable[[M], Awaitable[None]]
    ack_wait: float | None = None
    max_attempts: int | None = None
    async_middlewares: tuple[BaseAsyncMiddleware[M], ...] = ()
    sync_middlewares: tuple[BaseSyncMiddleware[M], ...] = ()

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
        tasks = Tasks(self.name)
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
                    tasks=tasks,
                )
                if burst:
                    await tasks.wait()
                    return
        finally:
            tasks.cancel()
            await psub.unsubscribe()

    async def _pull_and_handle(
        self, *,
        poll_sem: asyncio.Semaphore,
        worker_sem: asyncio.Semaphore,
        poll_delay: float,
        batch: int,
        psub: nats.js.JetStreamContext.PullSubscription,
        tasks: Tasks,
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
        for msg in msgs:
            tasks.start(self._handle_message(msg, worker_sem, tasks))

    async def _handle_message(
        self,
        msg: Msg,
        sem: asyncio.Semaphore,
        tasks: Tasks,
    ) -> None:
        pulse_task = asyncio.create_task(self._pulse(msg))
        event = None
        has_middlewares = bool(self.async_middlewares or self.sync_middlewares)
        try:
            async with sem:
                start = perf_counter()
                event = self.event.serializer.decode(msg.data)

                # trigger on_start hooks
                if has_middlewares:
                    ctx = Context(actor=self, message=event, _msg=msg)
                    for smw in self.sync_middlewares:
                        if smw.on_start is not BaseSyncMiddleware.on_start:
                            smw.on_start(ctx)
                    for amw in self.async_middlewares:
                        if amw.on_start is not BaseAsyncMiddleware.on_start:
                            tasks.start(amw.on_start(ctx))

                await self.handler(event)
        except (Exception, asyncio.CancelledError) as exc:
            pulse_task.cancel()
            logger.exception(f'Unhandled {type(exc).__name__} in "{self.name}" actor')
            await msg.nak()

            # trigger on_failure hooks
            if has_middlewares:
                ectx = ErrorContext(actor=self, message=event, exception=exc, _msg=msg)
                for smw in self.sync_middlewares:
                    if smw.on_failure is not BaseSyncMiddleware.on_failure:
                        smw.on_failure(ectx)
                for amw in self.async_middlewares:
                    if amw.on_failure is not BaseAsyncMiddleware.on_failure:
                        tasks.start(amw.on_failure(ectx))
        else:
            pulse_task.cancel()
            await msg.ack()

            # trigger on_success hooks
            if has_middlewares:
                duration = perf_counter() - start
                octx = OkContext(actor=self, message=event, _msg=msg, duration=duration)
                for smw in self.sync_middlewares:
                    if smw.on_success is not BaseSyncMiddleware.on_success:
                        smw.on_success(octx)
                for amw in self.async_middlewares:
                    if amw.on_success is not BaseAsyncMiddleware.on_success:
                        tasks.start(amw.on_success(octx))

    async def _pulse(self, msg: Msg) -> None:
        """Keep notifying nats server that the message handling is in progress.
        """
        if self.ack_wait is None:
            return
        while True:
            await msg.in_progress()
