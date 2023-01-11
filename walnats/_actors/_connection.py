from __future__ import annotations

import asyncio
from concurrent.futures import (
    Executor, ProcessPoolExecutor, ThreadPoolExecutor,
)
from contextlib import ExitStack
from dataclasses import dataclass

import nats
import nats.js

from ._actor import Actor
from ._execute_in import ExecuteIn


@dataclass(frozen=True)
class ConnectedActors:
    """A registry of :class:`walnats.Actor` instances.

    Like :class:`walnats.Actors` but connected to Nats server.

    Use it to listen to events. Don't instanciate directly,
    use :meth:`walnats.Actors.connect` instead.

    ::

        async with actors.connect() as conn:
            await conn.register()
            await conn.listen()
    """
    _js: nats.js.JetStreamContext
    _actors: tuple[Actor, ...]

    async def register(self) -> None:
        """Add nats consumers for actors.

        ::

            async with actors.connect() as conn:
                await conn.register()
        """
        tasks = []
        for actor in self._actors:
            task = asyncio.create_task(
                actor._add(self._js),
                name=f'actors/{actor.name}/add',
            )
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def listen(
        self, *,
        burst: bool = False,
        max_polls: int | None = None,
        poll_delay: float = 2,
        batch: int = 1,
        max_jobs: int = 16,
        max_processes: int | None = None,
        max_threads: int | None = None,
    ) -> None:
        """Listen Nats for events for all registered actors.

        Args:
            burst: try polling events for all actors only once, handle everything polled,
                and exit. It's useful for testing when you know there is alread a message
                in the queue when you start listening, and that's all you want to process.
            max_polls: how many polling requests can be active simultaneously.
                Default to the number of actors. You might want to set it to a lower
                value if you have more actors than free network sockets in the system.
                Then actors will take turns to polling, each turn taking poll_delay.
            poll_delay: how long each poll request will wait for messages.
                Low values will produce more requests but work better with low max_polls
                and better detect broken connections. See "keepalive" on wiki.
            batch: how many messages (max) to pull in a single poll request.
                Higher values reduce the number of network requests (and so give better
                performance) but can result in messages that wait on a specific instance
                for a job to be available while they could be delivered to another
                instance. In other words, leave it 1 (default) if you scale horizontally.
            max_jobs: how many jobs (handlers) can be running at the same time.
                Higher values put more strain on CPU but give better performance
                if the handlers are IO-bound and use a lot of async/await.
            max_processes: if an Actor is configured to run in a process,
                this is how many processes at most can be running at the same time.
                Defaults to the number of processors on the machine.
            max_threads: if an Actor is configured to run in a thread,
                this is how many threads at most can be running at the same time.
                Defaults to the number of processors on the machine + 4
                but at most 32.
        """
        assert max_polls is None or max_polls >= 1
        assert poll_delay >= 0
        assert batch >= 1
        assert max_jobs >= 1
        assert max_processes is None or max_processes >= 1
        assert max_threads is None or max_threads >= 1

        poll_sem = asyncio.Semaphore(max_polls or len(self._actors))
        global_sem = asyncio.Semaphore(max_jobs)
        thread_pool: ThreadPoolExecutor | None = None
        proc_pool: ProcessPoolExecutor | None = None
        with ExitStack() as stack:
            if any(a.execute_in == ExecuteIn.THREAD for a in self._actors):
                thread_pool = stack.enter_context(ThreadPoolExecutor(max_threads))
            if any(a.execute_in == ExecuteIn.PROCESS for a in self._actors):
                proc_pool = stack.enter_context(ProcessPoolExecutor(max_processes))
            tasks: list[asyncio.Task] = []
            executor: Executor | None
            for actor in self._actors:
                if actor.execute_in == ExecuteIn.THREAD:
                    executor = thread_pool
                elif actor.execute_in == ExecuteIn.PROCESS:
                    executor = proc_pool
                else:
                    executor = None
                coro = actor._listen(
                    js=self._js,
                    burst=burst,
                    poll_sem=poll_sem,
                    global_sem=global_sem,
                    batch=batch,
                    poll_delay=poll_delay,
                    executor=executor,
                )
                task = asyncio.create_task(coro, name=f'actors/{actor.name}')
                tasks.append(task)
            try:
                await asyncio.gather(*tasks)
            finally:
                for task in tasks:
                    task.cancel()
