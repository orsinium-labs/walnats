# Request/response

...

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
