from __future__ import annotations

import asyncio
from typing import Coroutine, final


@final
class Tasks:
    """Supervise multiple async tasks.
    """
    __slots__ = ('_tasks', '_cleanup_every', '_since_cleanup', '_name', '_done')
    _name: str
    _tasks: list[asyncio.Task]
    _cleanup_every: int
    _since_cleanup: int
    _done: bool

    def __init__(self, name: str) -> None:
        self._name = name
        self._tasks = []
        self._cleanup_every = 100
        self._since_cleanup = 0
        self._done = False

    def start(self, coro: Coroutine[None, None, None], name: str) -> None:
        """Create a new task and track it in the supervisor.
        """
        assert not self._done
        self._since_cleanup = (self._since_cleanup + 1) % self._cleanup_every
        if self._since_cleanup == 0:
            self._tasks = [t for t in self._tasks if not t.done()]
        task = asyncio.create_task(coro, name=name)
        self._tasks.append(task)

    def cancel(self) -> None:
        """Cancel all supervised tasks.
        """
        if self._done:
            return
        for task in self._tasks:
            task.cancel()

    async def wait(self) -> None:
        """Wait for all supervised tasks to finish.
        """
        assert not self._done
        await asyncio.gather(*self._tasks)
        self._done = True

    def __repr__(self) -> str:
        return f'{type(self).__name__}({repr(self._name)})'
