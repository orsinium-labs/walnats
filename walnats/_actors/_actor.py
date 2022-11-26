
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from logging import getLogger
from time import perf_counter
from typing import Awaitable, Callable, Generic, TypeVar

import nats.js
from nats.aio.msg import Msg

from .._context import Context, ErrorContext, OkContext
from .._events._event import BaseEvent, EventWithResponse
from .._tasks import Tasks
from ..middlewares import BaseMiddleware


T = TypeVar('T')
R = TypeVar('R')
logger = getLogger(__package__)


@dataclass(frozen=True)
class Actor(Generic[T, R]):
    name: str
    event: BaseEvent[T, R]
    handler: Callable[[T], Awaitable[R]]

    # settings for the nats consumer
    description: str | None = None
    ack_wait: float = 30
    max_attempts: int | None = None
    max_ack_pending: int = 1000

    # settings for local job processing
    middlewares: tuple[BaseMiddleware, ...] = ()
    max_jobs: int = 16

    @property
    def consumer_name(self) -> str:
        """Durable name for Nats JetStream consumer.
        """
        assert self.name
        return self.name

    @property
    def _consumer_config(self) -> nats.js.api.ConsumerConfig:
        """
        https://docs.nats.io/nats-concepts/jetstream/consumers#configuration
        """
        return nats.js.api.ConsumerConfig(
            durable_name=self.consumer_name,
            description=self.description,
            ack_wait=self.ack_wait,
            max_deliver=self.max_attempts,
            max_ack_pending=self.max_ack_pending
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
        job_sem: asyncio.Semaphore,
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
        actor_sem = asyncio.Semaphore(self.max_jobs)
        try:
            while True:
                await self._pull_and_handle(
                    poll_sem=poll_sem,
                    job_sem=job_sem,
                    actor_sem=actor_sem,
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
        job_sem: asyncio.Semaphore,
        actor_sem: asyncio.Semaphore,
        poll_delay: float,
        batch: int,
        psub: nats.js.JetStreamContext.PullSubscription,
        tasks: Tasks,
    ) -> None:
        # don't try polling new messages if there are no jobs to handle them
        if actor_sem.locked():
            await actor_sem.acquire()
            actor_sem.release()
        if job_sem.locked():
            await job_sem.acquire()
            job_sem.release()

        # poll messages
        async with poll_sem:
            try:
                msgs = await psub.fetch(batch=batch, timeout=poll_delay)
            except asyncio.TimeoutError:
                return

        # run jobs
        for msg in msgs:
            tasks.start(self._handle_message(
                msg=msg,
                job_sem=job_sem,
                actor_sem=actor_sem,
                tasks=tasks,
            ), name=f'actors/{self.name}/handle_message')

    async def _handle_message(
        self,
        msg: Msg,
        job_sem: asyncio.Semaphore,
        actor_sem: asyncio.Semaphore,
        tasks: Tasks,
    ) -> None:
        prefix = f'actors/{self.name}/'
        if msg.metadata.sequence:
            prefix += f'{msg.metadata.sequence.consumer}/'
        pulse_task = asyncio.create_task(
            self._pulse(msg),
            name=f'{prefix}pulse',
        )
        event = None
        has_middlewares = bool(self.middlewares or self.middlewares)
        try:
            async with actor_sem, job_sem:
                start = perf_counter()
                event = self.event.decode(msg.data)

                # trigger on_start hooks
                if has_middlewares:
                    ctx = Context(actor=self, message=event, _msg=msg)
                    for mw in self.middlewares:
                        coro = mw.on_start(ctx)
                        if coro is not None:
                            tasks.start(coro, name=f'{prefix}on_start')

                result = await self.handler(event)
        except (Exception, asyncio.CancelledError) as exc:
            pulse_task.cancel()
            logger.exception(f'Unhandled {type(exc).__name__} in "{self.name}" actor')
            tasks.start(msg.nak(), name=f'{prefix}nak')

            # trigger on_failure hooks
            if has_middlewares:
                ectx = ErrorContext(actor=self, message=event, exception=exc, _msg=msg)
                for mw in self.middlewares:
                    coro = mw.on_failure(ectx)
                    if coro is not None:
                        tasks.start(coro, name=f'{prefix}on_failure')
        else:
            pulse_task.cancel()
            await msg.ack()

            if isinstance(self.event, EventWithResponse):
                payload = self.event.encode_response(result)
                tasks.start(msg.respond(payload), name=f'{prefix}respond')

            # trigger on_success hooks
            if has_middlewares:
                duration = perf_counter() - start
                octx = OkContext(actor=self, message=event, _msg=msg, duration=duration)
                for mw in self.middlewares:
                    coro = mw.on_success(octx)
                    if coro is not None:
                        tasks.start(coro, name=f'{prefix}on_success')

    async def _pulse(self, msg: Msg) -> None:
        """Keep notifying nats server that the message handling is in progress.
        """
        while True:
            await asyncio.sleep(self.ack_wait / 2)
            await msg.in_progress()
