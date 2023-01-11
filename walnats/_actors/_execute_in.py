from __future__ import annotations

from enum import Enum


class ExecuteIn(Enum):
    """ Run the handler in the current thread, in a thread pool, in a process pool.

    This is the enum of possible values for :attr:`walnats.Actor.execute_in`.

    ::

        def generate_daily_report(_) -> None:
            ...

        GENERATE_DAILY_REPORT = walnats.Actor(
            'generate-daily-report', DAY_PASSED, generate_daily_report,
            execute_in=walnats.ExecuteIn.PROCESS,
        )

    """

    MAIN = 'main'
    """The default behavior, run the handler in the current ("main") thread.

    Use it for async/await handlers or sync but very fast handlers.
    """

    THREAD = 'thread'
    """Run the handler in a thread pool.

    Use it for slow IO-bound non-async/await handlers.

    The number of threads can be configured with ``max_threads`` argument
    of :meth:`walnats.types.ConnectedActors.listen`.
    """

    PROCESS = 'process'
    """Run the handler in a process pool.

    Use it for slow CPU-bound handlers. The handler must be non-async/await.

    The number of threads can be configured with ``max_processes`` argument
    of :meth:`walnats.types.ConnectedActors.listen`.
    """
