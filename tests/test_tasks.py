import asyncio

from walnats._tasks import Tasks


async def test_wait():
    t = Tasks('tasks')
    for _ in range(20):
        t.start(asyncio.sleep(.001), 'task')
    await t.wait()
    assert len(t._tasks) == 20
    for task in t._tasks:
        assert task.done()


async def test_cancel():
    t = Tasks('tasks')
    for _ in range(20):
        t.start(asyncio.sleep(.001), 'task')
    await asyncio.sleep(0)
    t.cancel()
    await asyncio.sleep(0)
    assert len(t._tasks) == 20
    for task in t._tasks:
        assert task.cancelled()


async def test_cleanup_old_cancelled():
    t = Tasks('tasks')
    for _ in range(91):
        t.start(asyncio.sleep(.001), 'task1')
    for _ in range(4):
        t.start(asyncio.sleep(.005), 'task2')
    # give tasks1 time to finish but not enough for tasks2
    await asyncio.sleep(0.002)
    # start more tasks, it should clean up tasks1 but leave tasks2
    for _ in range(9):
        t.start(asyncio.sleep(.001), 'task3')
    assert len(t._tasks) == 13
