# Periodic tasks

You often will have tasks that you need to execute periodically (for instance, every day or every 5 minutes) or by schedule (for instance, 5 days after today). For example, create a database backup every midnight or actualize a cache of orders every 5 minutes. Wouldn't it be great to have an event for that? Then you can get for the periodic tasks all the benefits of event-driven actors: scalability, distribution, retries, observability, and more.

Meet `walnats.Clock`. It's a worker that emits periodic events. To implement a periodic task, run the clock and subscribe to the event in any other place.

```{eval-rst}
.. autoclass:: walnats.Clock()
    :members:
```

## Tips

1. It might be a good idea to run a separate clock on each nats cluster so that in case of network failure between clusters, events will still be coming in each of them. When the connection is restored, Nats will make sure there are no duplicates.
1. The interval between events may be affected by CPU-bound tasks running in the same process. To avoid it, make sure to use {py:attr}`walnats.ExecuteIn.PROCESS` for all CPU-heavy actors running in the same instance as the clock.
1. If there is just one worker that needs a very specific schedule (for instance, it must be run daily at 12:03 and any other time won't do), prefer using {py:class}`walnats.decorators.filter_time`. If multiple workers need the same schedule (like being run once a day, doesn't matter when), prefer providing for them a separate Clock with a fitting duration.
