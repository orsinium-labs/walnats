# walnats

[Nats](https://nats.io/)-based event-driven background jobs and microservices framework.

Features:

+ Event-driven.
+ 100% type-safe.
+ Immutable and easy to test.
+ Explicit APIs, no magic.
+ Strict separation between publishers and subscribers.
+ Asyncio-based.
+ Nats-powered.
+ Exactly-once delivery.
+ Smart and configurable retries.
+ Many integrations.
+ Compatible. You can use walnats to emit events for non-walnats services or consume events emitted by non-walnats services. The tool is flexible enough to adapt to any format of the messages you use.

## Compared to other tools

Compared to other big Python frameworks for background jobs (like [celery](https://docs.celeryq.dev/en/stable/), [dramatiq](https://dramatiq.io/index.html), [rq](https://python-rq.org/), [huey](https://huey.readthedocs.io/en/latest/), and so on), the main difference from an implementation perspective is that walnats is younger and so had an opportunity to be designed around modern technologies right from the beginning. Namely, mypy-powered type safety, async/await-powered concurrency, and nats-powered persistency and distribution.

And when compared to **all** other Python frameworks for background jobs (including new async/await-based ones like [arq](https://arq-docs.helpmanual.io/), [pytask-io](https://github.com/joegasewicz/pytask-io), and [aiotasks](https://github.com/cr0hn/aiotasks)), the main difference is that Walnats is event-driven. While in all these frameworks the job scheduling is conceptually a function call over the network, in walnats publishers instead emit events to which any subscribers can subscribe at any point. This approach is called "[tell, don't ask](https://wiki.c2.com/?TellDontAsk)".

For example, when your webshop sends a parcel to a client, instead of directly calling `send_email` and `send_sms` actors like you'd do with Celery, with Walnats publisher will emit a single `parcel-sent` event, and that event will be delivered by Walnats to all interested actors. It gives you a few nice benefits:

1. Publisher makes only one network request.
1. When you add a new actor, you don't need to modify the publisher. That's especially cool for microservice architecture when the publisher and the actor can be different services owned by different teams.
1. It's easier to reason about. When you develop a microservice, you only need to know what events there are you can subscribe to and emit your own events without thinking too much about how all other services in the system work with these events.
1. It's easier to observe. Walnats directly translates events into Nats subjects and actors into Nats JetStream consumers. So, any Nats observability tool will give you great insights into what's going on in your system.

If you have a big distributed system, Walnats is for you. If all you want is to send emails in the background from your Django monolith or a little hobby project, you might find another framework a better fit.

Lastly, compared to you just taking [nats.py](https://github.com/nats-io/nats.py) and writing your service from scratch, Walnats does a better job at handling failures, load spikes, and corner cases. Walnats is "[designed for failure](https://www.v-wiki.net/design-for-failure/)". Distributed systems are hard, and you shouldn't embark on this journey alone.

## Installation

```bash
python3 -m pip install walnats
```

## Walnats in 30 seconds

Create a module with events, it should be shared across services:

```python
import walnats

COUNT = walnats.Event('counts', int)
#                 name ⤴  type ⤴
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
        #     ↑ create Nats JetStream streams
        for value in range(1000):
            await conn.emit(COUNT,  value)
            #         event ⤴  payload ⤴
            print(f'emitted {value}')
            await asyncio.sleep(1)

asyncio.run(run())
```

Create a subscriber (a service that listens to events):

```python
import asyncio
import walnats
from .events import COUNT

async def run() -> None:
    registry = walnats.Actors(
        walnats.Actor('print', COUNT,    print),
        #         name ⤴  event ⤴  handler ⤴
    )
    async with registry.connect() as conn:
        await conn.register()
        #     ↑ create Nats JetStream consumers
        await conn.listen()
        #     ↑ start all actors

asyncio.run(run())
```

That's it! Now you can run the services:

1. Run publisher: `python3 -m pub`
1. Run subscriber in another terminal window: `python3 -m sub`
1. Run another subscriber to see how the work is distributed across multiple instances: `python3 -m sub`
1. Stop a subscriber (`ctrl+c`) to see that no messages get lost.

This code is available in [examples/readme_demo](./examples/readme_demo/).
