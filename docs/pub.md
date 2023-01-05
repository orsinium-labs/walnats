# Publisher

Publisher is the code that emits events. It's up to you how you structure and run the publisher. It might be a web service, an actor, a CLI tool, or anything else.

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

[CloudEvents](https://cloudevents.io/) is a specification that describes the format of metadata for events. Walnats doesn't care about most of the data there but it can be useful if you use some third-party tools or consumers that can benefit from such metadata. If that's the case, you can pass a {py:class}`walnats.CloudEvent` instance as an argument into {py:meth}`walnats.types.ConnectedEvents.emit`. This metadata will be included into the Nats message headers according to the WIP specification: [NATS Protocol Binding for CloudEvents](https://github.com/cloudevents/spec/blob/main/cloudevents/bindings/nats-protocol-binding.md).

```{eval-rst}
.. autoclass:: walnats.CloudEvent
```
