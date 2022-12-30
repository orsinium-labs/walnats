# Publisher

## Connect to Nats

```{eval-rst}
.. autoclass:: walnats.Events
    :members:
```

## Emit events

```{eval-rst}
.. autoclass:: walnats.types.ConnectedEvents()
    :members:
```

## CloudEvents

[CloudEvents](https://cloudevents.io/) is a specification that describes the format of metadata for events. Walnats doesn't care about most of the data there but it can be useful if you use some third-party tools or consumers that can benefit from such metadata. If that's the case, you can pass a {py:class}`walnats.CloudEvent` instance as an argument into {py:meth}`walnats.types.ConnectedEvents.emit`. This metadata will be included into the Nats message headers according to the WIP specification: [NATS Protocol Binding for CloudEvents](https://github.com/cloudevents/spec/blob/main/cloudevents/bindings/nats-protocol-binding.md).

```{eval-rst}
.. autoclass:: walnats.CloudEvent
    :members:
```
