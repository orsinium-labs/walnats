# Events

When you design an event-driven architecture, one of the first things you should consider is which events you'll have.

## Declare events

Events should be stored in a separate library shared across all actors and producers that need it. This library will serve your schema registry and provide type safety for all code that emits or handles events.

To declare an event, you'll need to provide the event name and the model. The model can be a dataclass, a pydantic model, a protobuf message, or anything else that can be serialized. In this tutorial, we'll use a dataclass because it's available in stdlib.

```python
import walntas
from dataclasses import dataclass

@dataclass
class User:
    id: str
    name: str

USER_REGISTERED = walnats.Event('user-registered', User)
```

If you're curious, this is the full reference for the Event class:

```{eval-rst}
.. autoclass:: walnats.Event
```

## Limit events

```{eval-rst}
.. autoclass:: walnats.Limits
```

## Tips

Declaring events:

+ The event name should be a verb that describes what happened in the system. Examples: "user-registered", "parcel-delivered", "order-created".
+ Pick some case style and stick to it. I use kebab-case.
+ Choose the event name carefully. You cannot rename the event after it reaches the production. Well, you can, but that's very hard to do without loosing (or duplicating) messages because actors and producers are deployed independently.
+ If you have non-Python microservices, consider also using some kind of event registry, like [eventcatalog](https://github.com/boyney123/eventcatalog) or [BSR](https://docs.buf.build/bsr/introduction), so that event definition (and especially schemas for models) are available for all services.
+ Use `SCREAMING_SNAKE_CASE` for the variable where the event is assigned. Events are immutable, and so can be considered constants.
+ When you add a new field in an existing event, provide the default value for it. It is possible that the actor expecting the field is deployed before the producer, or an old event emitted by an old producer arrives. Always keep in mind backward compatibility. Changing a service is atomic and can be done in one deployment, changing multiple services isn't.

Which fields to include in the event model:

+ Include in the event fields that will be needed to many or all actors. For example, "parcel-status-changed" should include not only the parce ID in the database but also the old and the new status of the parcel. That way, the actors that do something only to the parcel moving in a specific status will be able to check the status without doing any database requests.
+ Do not include fields that are not needed or needed only for a handful of actors, it doesn't scale well. For example, if there is a "send-email" actor that reacts to "user-registered" event, trying to fit into the event all information needed for the email is a dead end. Each time you decide to add more information into email, you'll need to update not only the actor but also the producer of the event, which defeats the whole point of event-driven architecture. Producers (and hence the events) should not depend on the implementation of a specific actor.
+ When considering to include or not an event, you should think about scenario when the relevant database record has been updated after the event was emitted. For example, don't include user's email in the "user-registered" event. If they update their name, all actors sending emails should use the latest version. But you should include the user's email in the "user-email-changed" event, so that if the user changes email again before the first event is processed, both changes are properly handled by actors.

Modeling events for your system is like art, except if you do it wrong, everyone dies. The [awesome-event-patterns](https://github.com/boyney123/awesome-event-patterns) list has some good articles about designing events. That's a good place to get started.
