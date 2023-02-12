from __future__ import annotations

import asyncio
from typing import Coroutine, final


@final
class Tasks:
    """Supervise multiple async tasks.
    """
    __slots__ = ('_tasks', '_name', '_done')
    _name: str
    _tasks: set[asyncio.Task]
    _done: bool

    def __init__(self, name: str) -> None:
        self._name = name
        self._tasks = set()
        self._done = False

    def start(self, coro: Coroutine[None, None, None], name: str) -> None:
        """Create a new task and track it in the supervisor.
        """
        assert not self._done
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

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
