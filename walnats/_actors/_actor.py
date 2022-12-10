
from __future__ import annotations

import asyncio
from concurrent.futures import Executor
from dataclasses import dataclass
from logging import getLogger
from time import perf_counter
from typing import Awaitable, Callable, Generic, Literal, Sequence, TypeVar

import nats.js
from nats.aio.msg import Msg

from .._context import Context, ErrorContext, OkContext
from .._events._event import BaseEvent, EventWithResponse
from ._tasks import Tasks
from ..middlewares import Middleware


T = TypeVar('T')
R = TypeVar('R')
logger = getLogger(__package__)


@dataclass(frozen=True)
class Actor(Generic[T, R]):
    """A subscriber group that listens to a specific event.

    Args:
        name: the actor name. It is used as durable consumer name in Nats,
            and so must be unique and never change. If you ever change the name,
            a consumer with the old name will be left in Nats JetStream and will
            accumulate events (until a limit is reached, and you should have Limits).
        event: the event to listen to. Exactly one instance of the same Actor
            will receive a message. That means, you can run the same actor multiple times
            on different machines, and only one will receive a message. And not a single
            message will be lost.
        handler: the function to call when a message is received.
        description: the actor description, will be attached to the consumer name in Nats.
            Can be useful if you use observability tools for Nats.
        ack_wait: how many seconds to wait from the last update before trying to
            redeliver the message. Before calling the handler, a task will be started
            that periodically sends a pulse into Nats saying that the job is in progress.
            The pulse, hovewer, might not arrive in Nats if the network or machine dies
            or something has blocked the scheduler for too long.
        max_attempts: how many attempts Nats will make to deliver the message.
            The message is redelivered if the handler fails to handle it.
        max_ack_pending: how many messages can be in progress simultaneously
            accross the whole system. If the limit is reached, delivery of messages
            is suspended.
        middlewares: callbacks that are triggered at different stages of message handling.
            Most of the time, you'll need regular decorators instead. Middlewares are
            useful when you need an additional context, like how many times the message
            was redelivered. In particular, for logs, metrics, alerts.
        max_jobs: how many jobs can be running simultaneously in this actor
            on this machine. The best number depends on available resources and
            the handler performance. Keep it low for slow handlers, keep it high for
            highly concurrent handlers.
        job_timeout: how long at most the handler execution can take for a single message.
            If this timeout is reached, asyncio.CancelledError is raised in handler, and
            then all the same things happen as for regular failure: on_failure hooks,
            log message, nak. Doesn't do anything for sync jobs without `execute_in`
            specified.
        execute_in: set it to run the handler in a thread or in a process.
            Use threads for slow IO-bound non-async/await handlers.
            Use processes for slow CPU-bound handlers.
            For running in a process, the handler and the message must be pickle-able.
            If ``execute_in`` is set, the handler must be non-async/await.
        retry_delay: a sequence of delays (in seconds) for each retry.
            If the attempt number is higher than the sequence len, the las item (-1)
            will be used. The default value is `(1, 2, 4, 8)`, so third retry will be 4s,
            5th will be 8s, and 12th will still be 8.
            The delay is used only when the message is explicitly nak'ed. If instead
            the whole instance explodes or there is a network issue, the message
            will be redelivered as soon as `ack_wait` is reached.
        pulse: keep sending pulse into Nats JetStream while processing the message.
            The pulse signal makes sure that the message won't be redelivered to another
            instance of actor while this one is in progress. Disabling the pulse will
            prevent the message being stuck if a handler stucks, but that also means
            the message must be processed faster that `ack_wait`.
    """
    name: str
    event: BaseEvent[T, R]
    handler: Callable[[T], Awaitable[R] | R]

    # settings for the nats consumer
    description: str | None = None
    ack_wait: float = 16
    max_attempts: int | None = None
    max_ack_pending: int = 1000

    # settings for local job processing
    middlewares: tuple[Middleware, ...] = ()
    max_jobs: int = 16
    job_timeout: float = 32
    execute_in: Literal['thread', 'process'] | None = None
    retry_delay: Sequence[float] = (1, 2, 4, 8)
    pulse: bool = True

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
            max_ack_pending=self.max_ack_pending,
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
        executor: Executor | None,
    ) -> None:
        """Subscribe to the stream, pull relevant messages, and run the handler for each.

        See SubConnection.listen for the list of arguments.
        """
        tasks = Tasks(self.name)
        psub = await js.pull_subscribe_bind(
            durable=self.consumer_name,
            stream=self.event.stream_name,
            # pending_msgs_limit=batch,
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
                    executor=executor,
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
        executor: Executor | None,
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
                executor=executor,
            ), name=f'actors/{self.name}/handle_message')

    async def _handle_message(
        self,
        msg: Msg,
        job_sem: asyncio.Semaphore,
        actor_sem: asyncio.Semaphore,
        tasks: Tasks,
        executor: Executor | None,
    ) -> None:
        prefix = f'actors/{self.name}/'
        if msg.metadata.sequence:
            prefix += f'{msg.metadata.sequence.stream}/'
        if self.pulse:
            pulse_task = asyncio.create_task(
                self._pulse(msg),
                name=f'{prefix}pulse',
            )
        event = None
        try:
            async with actor_sem, job_sem:
                start = perf_counter()
                event = self.event.decode(msg.data)

                # trigger on_start hooks
                if self.middlewares:
                    ctx = Context(actor=self, message=event, _msg=msg)
                    for mw in self.middlewares:
                        coro = mw.on_start(ctx)
                        if coro is not None:
                            tasks.start(coro, name=f'{prefix}on_start')

                if executor is not None:
                    loop = asyncio.get_running_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(executor, self.handler, event),
                        timeout=self.job_timeout,
                    )
                else:
                    result = self.handler(event)
                    if asyncio.iscoroutine(result):
                        result = await asyncio.wait_for(
                            result,
                            timeout=self.job_timeout,
                        )
        except (Exception, asyncio.CancelledError) as exc:
            pulse_task.cancel()
            logger.exception(f'Unhandled {type(exc).__name__} in "{self.name}" actor')
            tasks.start(msg.nak(delay=self._get_nak_delay(msg)), name=f'{prefix}nak')

            # trigger on_failure hooks
            if self.middlewares:
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
                reply = msg.headers.get('Walnats-Reply') if msg.headers else None
                if reply is not None:
                    coro = msg._client.publish(reply, payload, headers=msg.headers)
                    tasks.start(coro, name=f'{prefix}respond')

            # trigger on_success hooks
            if self.middlewares:
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

    def _get_nak_delay(self, msg: Msg) -> float:
        delays = self.retry_delay
        if not delays:
            return 0
        attempt = msg.metadata.num_delivered
        if attempt is None:
            return delays[0]
        if attempt >= len(delays):
            return delays[-1]
        return delays[attempt]
