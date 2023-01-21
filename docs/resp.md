# Request/response

If possible, you should try to design your system as a [directed acyclic graph](https://en.wikipedia.org/wiki/Directed_acyclic_graph) where there is only one producer for each event type, and the producer doesn't care how the events it emits are handled. Sometimes, you'll have loops when there are two actors and each can also produce an event in which the other actor is interested. And in some rare occasions, you'll have a producer that when emitting an event will need to wait for a response from an actor to this particular event. This is known as the request/response pattern and walnats provides support for it out-of-the-box.

The internal implementation is similar to [Request-Reply](https://docs.nats.io/nats-concepts/core-nats/reqreply) pattern in Nats. There is a difference, though. Nats implements it only for core Nats, without JetStream, and so it cannot be used with Nats JetStream consumers (and so with walnats actors). Walnats fixes it by providing its own implementation of the pattern on top of Nats. However, there is still no persistency for responses. Whatever response the actor sends, will be emitted through the core Nats. If there is a network failure or the producer gets restarted, the response will get lost. The idea is that the response matters only right now and only for this specific producer. If you need persistency, explicitly use events and actors for responses as well.

There are just a few changes you need to make for sending and receiving responses:

1. Make a copy of Event with {py:meth}`walnats.Event.with_response`.
1. Emit an event for this copy using {py:meth}`walnats.types.ConnectedEvents.request`. The method will return the result.
1. Return the result from the handler.

```python
# events
COUNT_WORDS = walnats.Event('count-words', str).with_response(int)

# actors
def count_words(text: str) -> int:
    return len(text.split())

WORD_COUNTER = walnats.Actor('count-words', COUNT_WORDS, count_words)

# events
events = walnats.Events(COUNT_WORDS)
async with events.connect() as conn:
    count = await conn.request(COUNT_WORDS, 'some random text')
```

## API

```{eval-rst}
.. automethod:: walnats.Event.with_response
.. autoclass:: walnats.types.EventWithResponse()
```

```{eval-rst}
.. automethod:: walnats.types.ConnectedEvents.request
```
