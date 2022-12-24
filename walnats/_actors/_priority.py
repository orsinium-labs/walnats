from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from enum import Enum
from typing import AsyncIterator


class Priority(Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2

    @asynccontextmanager
    async def acquire(self, sem: asyncio.Semaphore) -> AsyncIterator[None]:
        """Acquire semaphore with priority.
        """
        for _ in range(self.value):
            async with sem:
                await asyncio.sleep(0)
        async with sem:
            yield
