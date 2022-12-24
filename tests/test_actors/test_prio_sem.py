from __future__ import annotations

import asyncio
import random

import hypothesis
from hypothesis import strategies

from walnats._actors._priority import Priority


@hypothesis.given(
    sem_value=strategies.integers(1, 150),
    job_count=strategies.integers(1, 200),
)
async def test_priority_one_batch(sem_value, job_count):
    """
    Run multiple workers at the same time
    and ensure higher priority jobs always go first.
    """
    results = []

    async def worker(sem, prio: Priority):
        async with prio.acquire(sem):
            results.append(prio)
            await asyncio.sleep(0)

    tasks = []
    sem = asyncio.BoundedSemaphore(sem_value)
    for _ in range(job_count):
        prio = random.choice(list(Priority))
        tasks.append(worker(sem, prio))
    await asyncio.gather(*tasks)

    assert len(results) == job_count
    for p1, p2 in zip(results, results[1:]):
        assert p1.value <= p2.value


@hypothesis.given(
    sem_value=strategies.integers(1, 180),
    job_count=strategies.integers(1, 40),
    group_count=strategies.integers(1, 4),
)
async def test_priority_multiple_batches(sem_value, job_count, group_count):
    """
    Run multiple workers in multiple batches
    and ensure higher priority jobs from the same batch always go first.
    """
    results = []

    async def worker(sem, prio: Priority, group):
        async with prio.acquire(sem):
            results.append((prio, group))
            await asyncio.sleep(.0001)

    tasks = []
    sem = asyncio.BoundedSemaphore(sem_value)
    for group in range(group_count):
        for _ in range(job_count):
            prio = random.choice(list(Priority))
            tasks.append(worker(sem, prio, group))
        await asyncio.sleep(.0015)
    await asyncio.gather(*tasks)

    assert len(results) == job_count * group_count
    for group in range(group_count):
        for (p1, g1), (p2, g2) in zip(results, results[1:]):
            if g1 != group or g2 != group:
                continue
            assert p1.value <= p2.value
