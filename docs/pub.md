# Publisher

The publisher is the code that emits events. It's up to you how you structure and run the publisher. It might be a web service, an actor, a CLI tool, or anything else.

All you need to do:

1. Collect all events you're going to emit from this app into `walnats.Events` registry.
2. Call `register` to create or update Nats JetStream streams.
3. Call `emit` at any point to emit an event.

```python
events = walnats.Events(USER_CREATED, USER_UPDATED)
async with events.connect() as conn:
    await conn.register()
    ...
    for user in new_users:
        await conn.emit(USER_CREATED, user)
```

## Designing for failure

This section gives a few insights into how to make event producers more resilient.

+ **Outbox**. If the nats client we use ([nats.py](https://github.com/nats-io/nats.py)) gets disconnected from the server, it tries to reconnect in the background. If you try sending a message while the connection is lost, that message will be put into the pending queue and sent after the connection is restored. Hence, successful `emit` doesn't mean the message will be delivered to Nats server. The client might be shut down before it restores the connection with the server. You can adjust this behavior in several ways:
  + Call {py:meth}`walnats.types.ConnectedEvents.emit` with `sync=True`. Then walnats will make sure the message is delivered to Nats JetStream before returning.
  + Call {py:func}`nats.connect` with `pending_size=0` (and pass this connection into `walnats.Events.connect`). The argument sets the maximum size in bytes of the pending messages queue. Setting it to zero disables the outbox altogether. When the connection is lost, you try to emit an event, and the limit is reached, the client will raise {py:exc}`nats.errors.OutboundBufferLimitError`.
+ **Transactions**. Use transactions for database changes. For example, for SQLAlchemy, see [Transactions and Connection Management](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html). That way, if I `emit` fails, the database changes will be rolled back, and then the whole operation you did can be safely retried.
+ **Deduplication**. If you have retries for the operation that emits an event, it's possible that the operation (try to guess) will be retried, and so `emit` will be called twice. To avoid the same event to be emitted twice, you can provide a `uid` argument for {py:meth}`walnats.types.ConnectedEvents.emit` (which has to be a unique identifier of the message), and Nats will make sure to ignore duplicates. The default deduplication window is 2 minutes.

If you want to know everything about what publishers can do with events, check out the API docs below. If you're just getting started, feel free to skip to the next chapter: [Actors](actors).

## API

```{eval-rst}
.. autoclass:: walnats.Events
    :members:
```

```{eval-rst}
.. autoclass:: walnats.types.ConnectedEvents()
    :members: register, emit
```

## CloudEvents

[CloudEvents](https://cloudevents.io/) is a specification that describes the format of metadata for events. Walnats doesn't care about most of the data there but it can be useful if you use some third-party tools or consumers that can benefit from such metadata. If that's the case, you can pass a {py:class}`walnats.CloudEvent` instance as an argument into {py:meth}`walnats.types.ConnectedEvents.emit`. This metadata will be included in the Nats message headers according to the WIP specification: [NATS Protocol Binding for CloudEvents](https://github.com/cloudevents/spec/blob/main/cloudevents/bindings/nats-protocol-binding.md).

```{eval-rst}
.. autoclass:: walnats.CloudEvent
```
