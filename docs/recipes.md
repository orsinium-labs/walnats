# Recipes

This page covers common usage patterns of walnats.

## Passing dependencies into handlers

The handler can be any callable object (like a method or a class with a `__call__` method), not necessarily a function. You can use this fact to bind the handler's dependencies as class attributes:

```python
@dataclass
class EmailService:
    db: Database

    async def send_email(self, user: User) -> None:
        await self.db.do_something(user)

async def run() -> None:
    db = await Database.connect(...)
    s = EmailService(db)
    actor = walnats.Actor('send-email', USER_REGISTERED, s.send_email)
    actors = walnats.Actors(actor)
    ...
```

## Routing events based on a value

Often, you'll have actors that need to do something only for an event with a specific value in some field. For example, send email only for a parcel update only when it moves in a specific status or write audit logs only for non-admin users. The easiest solution is to simply check the condition at the beginning of the handler, but that means the actor will have to receive, decode, and check every event and do something useful only to a small portion of them.

A better solution (in some situations) might be to provide separate events for each possible value of the field. Assuming that there is a small and well-known set of possible values.

```python
# events
LIGHT_CHANGES = {}
for color in {'red', 'yellow', 'green'}:
    LIGHT_CHANGES[color] = walnats.Event(f'light-change-{color}', int)

# publisher
events = walnats.Events(*LIGHT_CHANGES.values())
async with events.connect() as conn:
    ...
    lights = ['red', 'yellow', 'green', 'yellow']
    for light in itertools.cycle(lights):
        await conn.emit(LIGHT_CHANGES[light], 0)

# subscriber
RELEASE_CARS = walnats.Actor(
    'release-cars', LIGHT_CHANGES['green'], release_cars,
)
```

If there is a handler that needs all updates, register it as multiple actors:

```python
loggers = []
for event in LIGHT_CHANGES.values():
    actor = walnats.Actor(f'log', event, log)
    loggers.append(actor)

actors = walnats.Actors(*loggers)
```
