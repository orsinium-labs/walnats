
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from time import perf_counter
from typing import (
    TYPE_CHECKING, Awaitable, Callable, Generic, Sequence, TypeVar,
)

import nats.js
from nats.aio.msg import Msg

from .._constants import HEADER_DELAY, HEADER_REPLY
from .._context import Context, ErrorContext, OkContext
from .._events._event import BaseEvent, EventWithResponse
from .._tasks import Tasks
from ._execute_in import ExecuteIn
from ._priority import Priority


if TYPE_CHECKING:
    from concurrent.futures import Executor

    from ..middlewares import Middleware


T = TypeVar('T')
R = TypeVar('R')
logger = getLogger('walnats.actor')


@dataclass(frozen=True)
class Actor(Generic[T, R]):
    """A subscriber group that listens to a specific :class:`walnats.Event`.

    ::

        async def send_email(user: User) -> None:
            ...

        SEND_EMAIL = walnats.Actor('send-email', USER_CREATED, send_email)

    The following options are submitted into Nats JetStream and so
    cannot be ever changed after the actor is registered for the first time:

    * ``description``
    * ``ack_wait``
    * ``max_attempts``
    * ``max_ack_pending``

    """

    name: str
    """
    The actor name. It is used as durable consumer name in Nats,
    and so must be unique per event and never change. If you ever change the name,
    a consumer with the old name will be left in Nats JetStream and will
    accumulate events (until a limit is reached, and you should have Limits).
    """

    event: BaseEvent[T, R]
    """
    The event to listen to. Exactly one instance of the same Actor
    will receive a message. That means, you can run the same actor multiple times
    on different machines, and only one will receive a message. And not a single
    message will be lost.
    """

    handler: Callable[[T], Awaitable[R] | R]
    """
    The function to call when a message is received.
    """

    # settings for the nats consumer

    description: str | None = None
    """
    The actor description, will be attached to the consumer name in Nats.
    Can be useful if you use observability tools for Nats.
    """

    ack_wait: float = 16
    """
    How many seconds to wait from the last update before trying to
    redeliver the message. Before calling the handler, a task will be started
    that periodically sends a pulse into Nats saying that the job is in progress.
    The pulse, hovewer, might not arrive in Nats if the network or machine dies
    or something has blocked the scheduler for too long.
    """

    max_attempts: int | None = None
    """
    How many attempts Nats will make to deliver the message.
    The message is redelivered if the handler fails to handle it.
    """

    max_ack_pending: int = 1000
    """
    How many messages can be in progress simultaneously across the whole system.
    If the limit is reached, delivery of messages is suspended.
    """

    # settings for local job processing

    middlewares: tuple[Middleware, ...] = ()
    """
    Callbacks that are triggered at different stages of message handling.
    Most of the time, you'll need regular decorators instead. Middlewares are
    useful when you need an additional context, like how many times the message
    was redelivered. In particular, for logs, metrics, alerts.
    Middlewares cannot be used for flow control.
    """

    max_jobs: int = 16
    """
    How many jobs can be running simultaneously in this actor on this machine.
    The best number depends on available resources and the handler performance.
    Keep it low for slow handlers, keep it high for highly concurrent handlers.
    """

    job_timeout: float = 32
    """
    How long at most the handler execution can take for a single message.
    If this timeout is reached, asyncio.CancelledError is raised in handler, and
    then all the same things happen as for regular failure: on_failure hooks,
    log message, nak. Doesn't do anything for sync jobs without `execute_in` specified.
    """

    execute_in: ExecuteIn = ExecuteIn.MAIN
    """
    Run the handler in the current thread, in a separate thread pool, in a process pool.
    """

    retry_delay: Sequence[float] = (.5, 1, 2, 4)
    """
    A sequence of delays (in seconds) for each retry.
    If the attempt number is higher than the sequence len, the las item (-1)
    will be used. The default value is `(1, 2, 4, 8)`, so third retry will be 4s,
    5th will be 8s, and 12th will still be 8.

    The delay is used only when the message is explicitly nak'ed. If instead
    the whole instance explodes or there is a network issue, the message
    will be redelivered as soon as `ack_wait` is reached.
    """

    pulse: bool = True
    """
    Keep sending pulse into Nats JetStream while processing the message.
    The pulse signal makes sure that the message won't be redelivered to another
    instance of actor while this one is in progress. Disabling the pulse will
    prevent the message being stuck if a handler stucks, but that also means
    the message must be processed faster that `ack_wait`.
    """

    priority: Priority = Priority.NORMAL
    """
    Priority of the actor compared to other actors. Actors with a higher
    priority have a higher chance to get started earlier. Longer an actor waits
    its turn, higher its priority gets.
    """

    _now: Callable[[], float] = field(default=lambda: datetime.utcnow().timestamp())

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
        global_sem: asyncio.Semaphore,
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
            pending_msgs_limit=batch,
        )
        actor_sem = asyncio.Semaphore(self.max_jobs)
        try:
            while True:
                await self._pull_and_handle(
                    poll_sem=poll_sem,
                    global_sem=global_sem,
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
        global_sem: asyncio.Semaphore,
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
        if global_sem.locked():
            await global_sem.acquire()
            global_sem.release()

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
                global_sem=global_sem,
                actor_sem=actor_sem,
                tasks=tasks,
                executor=executor,
            ), name=f'actors/{self.name}/handle_message')

    async def _handle_message(
        self,
        msg: Msg,
        global_sem: asyncio.Semaphore,
        actor_sem: asyncio.Semaphore,
        tasks: Tasks,
        executor: Executor | None,
    ) -> None:
        prefix = f'actors/{self.name}/'
        if msg.metadata.sequence:
            prefix += f'{msg.metadata.sequence.stream}/'

        # if the message should be delayed, nak it with the delay and skip the message
        delay_str = (msg.headers or {}).get(HEADER_DELAY)
        if delay_str:
            delayed_until = float(delay_str)
            delay_left = delayed_until - self._now()
            if delay_left > .001:
                await msg.nak(delay=delay_left)
                return

        pulse_task: asyncio.Task[None] | None = None
        if self.pulse:
            pulse_task = asyncio.create_task(
                self._pulse(msg),
                name=f'{prefix}pulse',
            )
        event = None
        try:
            async with actor_sem, self.priority.acquire(global_sem):
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
            if pulse_task is not None:
                pulse_task.cancel()
            logger.exception(f'Unhandled {type(exc).__name__} in "{self.name}" actor')
            nak_coro = msg.nak(delay=self._get_nak_delay(msg.metadata.num_delivered))
            tasks.start(nak_coro, name=f'{prefix}nak')

            # trigger on_failure hooks
            if self.middlewares:
                ectx = ErrorContext(actor=self, message=event, exception=exc, _msg=msg)
                for mw in self.middlewares:
                    coro = mw.on_failure(ectx)
                    if coro is not None:
                        tasks.start(coro, name=f'{prefix}on_failure')
        else:
            if pulse_task is not None:
                pulse_task.cancel()
            await msg.ack()

            if isinstance(self.event, EventWithResponse):
                payload = self.event.encode_response(result)
                reply = msg.headers.get(HEADER_REPLY) if msg.headers else None
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

    def _get_nak_delay(self, attempt: int | None) -> float:
        delays = self.retry_delay
        if not delays:
            return 0
        if attempt is None:
            return delays[0]
        assert attempt >= 0
        if attempt >= len(delays):
            return delays[-1]
        return delays[attempt]
