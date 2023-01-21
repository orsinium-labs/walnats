# Actors

Actors listen to events and do something ("act") when an event occurs.

## Implement handlers

The handler is a function (sync or async, async is better) that accepts the event and acts on it. For example:

```python
async def send_email(user: User) -> None:
    ...
```

That's it. The handler knows nothing about Nats, Walnats, or the publisher. That means it's dead simple to test, refactor, or reuse with another framework. This pattern is known as [Functional core, imperative shell](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell). The handler is the functional core, and walnats is the imperative shell that you don't need to test (at least not in the unit tests).

## Declare actors

The actor connects together the event and the handler. Each actor also has a name that must be unique for all actors subscribed to the same event.

```python
WELCOME_USER = walnats.Actor(
    'welcome-user', USER_REGISTERED, send_email,
)
```

That's all you need to get started. Below are the API docs covering different configuration options you can specify for an actor. They allow you to adjust the actor's behavior in case there are too many messages or a handler failure. We'll also talk about handling high loads and failures in the [Subscriber](sub) section. So, you can skip the rest of the page for now if you're only getting started.

## API

```{eval-rst}
.. autoclass:: walnats.Actor()
    :members:
.. autoclass:: walnats.Priority()
    :members:
.. autoclass:: walnats.ExecuteIn()
    :members:
```
