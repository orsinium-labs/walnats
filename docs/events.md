# Events

Designing an event-driven architecture starts with describing services and events you're going to have. And so walnats-based project starts with defining events too.

## Declare events

Events should be stored in a separate library shared across all actors and producers that need it. This library will serve your schema registry and provide type safety for all code that emits or handles events.

To declare an event, you'll need to provide the event name and the schema:

+ The name is used to identify a specific event, and so must be unique across the system. You can never change it without breaking things, so choose it carefully. Prefer a name that tells what happened. For example, "order-created".
+ The schema can be a [dataclass](https://docs.python.org/3/library/dataclasses.html), a [pydantic](https://pydantic-docs.helpmanual.io/) model, a [protobuf](https://developers.google.com/protocol-buffers/docs/pythontutorial) message, or anything else that can be serialized. In this tutorial, we'll use a dataclass because it's available in stdlib.

```python
import walnats
from dataclasses import dataclass

@dataclass
class User:
    id: str
    name: str

USER_REGISTERED = walnats.Event('user-registered', User)
```

If you're curious, this is the full reference for the Event class:

```{eval-rst}
.. autoclass:: walnats.Event()
    :members: name, schema, serializer, description, limits, subject_name, stream_name
```

## Limit events

A distributed system should be designed with a fault-tolerance in mind. Walnats will take care of redelivering failed messages in case a handler fails, an instance dies, or any other emergency. But for how long should it try redeliveries? And what if there are suddenly too many messages? That differs from event to event, depending on the business model and the system you build, and so only you can answer these questions. That's why you should specify limits for all events. The limits describe how long messages can be stored, how much space they can take, how many of them can be in total, and so on. When a limit is reached, the Nats server will drop old messages to fit into the limit.

```python
USER_REGISTERED = walnats.Event(
    'user-registered', User,
    # store at most 10k messages
    limits=walnats.Limits(messages=10_000),
)
```

This is the reference of Limits with all limits you can set:

```{eval-rst}
.. autoclass:: walnats.Limits()
    :members:
```

## Exceptions

```{eval-rst}
.. autoexception:: walnats.StreamConfigError()
    :show-inheritance:
.. autoexception:: walnats.StreamExistsError()
    :show-inheritance:
```

## Tips

Declaring events:

+ **Descriptive name**. The event name should be a verb that describes what happened in the system. Examples: "user-registered", "parcel-delivered", "order-created".
+ **Persistent name**. Choose the event name carefully. You cannot rename the event after it reaches production. Well, you can, but that's very hard to do without losing (or duplicating) messages because actors and producers are deployed independently.
+ **Registry**. If you have non-Python microservices, consider also using some kind of event registry, like [eventcatalog](https://github.com/boyney123/eventcatalog) or [BSR](https://docs.buf.build/bsr/introduction), so that event definition (and especially schemas) are available for all services.
+ Use `SCREAMING_SNAKE_CASE` for the variable where the event is assigned. Events are immutable, and so can be considered constants.
+ **Defaults**. When you add a new field in an existing event, provide the default value for it. It is possible that the actor expecting the field is deployed before the producer, or an old event emitted by an old producer arrives. Always keep in mind backward compatibility. Changing a service is atomic and can be done in one deployment, changing multiple services isn't.
+ **Versioning**. Make sure that when you change the limits, {py:meth}`walnats.ConnectedEvents.register` is executed only in the latest version of your app. For example, if v1 of your service sets `max_age=60`, v2 sets `max_age=120`, and then so happened that v1 calls `register` after v2 did that, v1 will negate the changes made by v1. To avoid the issue, call `register` only once the application start and make sure that if the app is restarted, it will be replaced by the latest version.

Which fields to include in the event schema:

+ Include in the event fields that will be needed for many or all actors. For example, "parcel-status-changed" should include not only the parcel ID in the database but also the old and the new status of the parcel. That way, the actors that do something only to the parcel moving in a specific status will be able to check the status without doing any database requests.
+ Do not include fields that are not needed or needed only for a handful of actors, it doesn't scale well. For example, if there is a "send-email" actor that reacts to "user-registered" event, trying to fit into the event all information needed for the email is a dead end. Each time you decide to add more information to an email, you'll need to update not only the actor but also the producer of the event, which defeats the whole point of event-driven architecture. Producers (and hence the events) should not depend on the implementation of a specific actor.
+ When considering whether to include or not an event, you should think about a scenario when the relevant database record has been updated after the event was emitted. For example, don't include the user's email in the "user-registered" event. If they update their name, all actors sending emails should use the latest version. But you should include the user's email in the "user-email-changed" event so that if the user changes email again before the first event is processed, both changes are properly handled by actors.

Modeling events for your system is like art, except if you do it wrong, everyone dies. The [awesome-event-patterns](https://github.com/boyney123/awesome-event-patterns) list has some good articles about designing events. That's a good place to get started.
