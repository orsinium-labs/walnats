# Subscriber

The subscriber runs a set of actors. It's up to you to provide CLI for the subscriber (or another way you want to run it), connect to the database, decide what actors you want to run where, and all that stuff.

What you need to do:

1. Collect all actors you want to run into the `walnats.Actors` registry.
2. Call `register` to create Nats JetStream consumers.
3. Call `listen` to start listening for events.

```python
actors = walnats.Actors(SEND_EMAIL, SEND_SMS)
async with actors.connect() as conn:
    await conn.register()
    await conn.listen()
```

Below are the API docs that list all options available for connecting and listening. You can scroll past them and go directly to the sections covering the handling of failures and the high load.

## API

```{eval-rst}
.. autoclass:: walnats.Actors
    :members:
.. autoclass:: walnats.types.ConnectedActors()
    :members:
```

## Design for high load

Walnats does its best to balance the load between actors, but exact numbers and strategies highly depend on the type of jobs you have, and that's something that only you may know.

* You can run multiple processes, each having its own walnats event listener. Either directly with [multiprocessing](https://docs.python.org/3/library/multiprocessing.html) or running the whole application multiple times. If you use [supervisord](http://supervisord.org/), consider adjusting the `numprocs` option based on how many cores the target machine has.
* The whole idea of async/await is to switch to CPU-bound work while waiting for an IO-bound response. For example, while we're waiting for a database response to a query, we can prepare and run another query. So, make sure there is always work to do while in `await`. You can do that by increasing the `max_jobs` value in both individual actors and `listen`, running more actors on the same machine, and actively using async/await in your code, with `asyncio.gather` and all.
* After some point, increasing `max_jobs` doesn't bring any value. This is the point when there is already more than enough work to do while in `await`, and so blocking operations start making the pause at `await` much longer than it is needed. It will make every job slower, and you'd better scale with more processes or machines instead.
* Keep in mind that all system resources are limited, and some limits are smaller than you might think. For example, the number of files or network connections that can be opened simultaneously. Again, having a smaller `max_jobs` (and in the case of network connections, `max_polls`) might help.
* If you have a long-running CPU-bound task, make sure to run it in a separate process poll by specifying `execute_in`.

## Design for failure

1. Keep in mind that your code can explode at any point, especially if you work a lot with external services and third-party APIs. Walnats will take care of retries, but it's on you to make sure nothing is left half-done in case of a failure ("Atomicity" part of [ACID](https://en.wikipedia.org/wiki/ACID)). For database queries, use a transaction. For network requests, keep them closer to the end and retry just the requests in case of failures. For file writes, write a temporary file first, and then copy it in the right place.
1. Make sure to have a reasonable `ack_wait` value. A too high number means the event might arrive when nobody needs the result ([real-time system](https://en.wikipedia.org/wiki/Real-time_computing)). Too low value might mean that walnats didn't get enough time to send an "in progress" pulse into Nats, and so the message was re-delivered to another instance of the actor while the first one hasn't failed.
1. The job may freeze. Make sure you specify timeouts for all network requests and that the actor itself has a low enough `job_timeout` value.
1. Some errors are caused by deterministic bugs, so no amount of retries can fix them. Make sure to specify `max_attempts` for the actor and `limits` for the event.
1. Make sure you have error reporting in place. Walnats provides out-of-the-box middleware for Sentry ({py:class}`walnats.middlewares.SentryMiddleware`), but you can always write your own middleware for whatever service you use.
