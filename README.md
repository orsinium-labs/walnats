# walnats

Nats-based event-driven background jobs and microservices framework.

Features:

+ Event-driven.
+ 100% type safe.
+ Immutable and easy to test.
+ Explicit APIs, no magic.
+ Clear separation between publishers and subscribers.
+ Asyncio-based.
+ Nats-powered.
+ Compatible. You can use walnats to emit events for non-walnats services or consume event emitted by non-walnats services. The tools is flexible enough to adapt for any format of the messages you use.

## Walnats in 30 seconds

Create a module with events, it should be shared across services:

```python
import walnats

COUNT = walnats.Event('counts', int)
```

Create publisher (a service that generates events):

```python
import asyncio
import walnats
from .events import COUNT

async def run() -> None:
    events = walnats.Events(COUNT)
    async with events.connect() as conn:
        await conn.register()
        for i in range(1000):
            await conn.emit(COUNT, i)
            print(f'emitted {i}')
            await asyncio.sleep(1)

asyncio.run(run())
```

Create subscriber (a service that listens to events):

```python
import asyncio
import walnats
from .events import COUNT

async def run_subscriber() -> None:
    registry = walnats.Actors(
        walnats.Actor('print', COUNT, print),
    )
    async with registry.connect() as conn:
        await conn.register()
        await conn.listen()

asyncio.run(run_subscriber())
```

That's it! Now you can run the services:

1. Run publisher: `python3 -m pub`
1. Run subscriber in another terminal window: `python3 -m sub`
1. Run another subscriber to see how the work is distributed across multiple instances: `python3 -m sub`
1. Stop a subscriber (`ctrl+c`) to see that no messages get lost.

This code is available in [examples/readme_demo](./examples/readme_demo/).
