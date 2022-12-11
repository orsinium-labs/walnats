# Serializers

## Custom serializers

```{eval-rst}
.. autoclass:: walnats.serializers.Serializer
    :members:
```

## Autodetected

```{eval-rst}
.. autoclass:: walnats.serializers.BytesSerializer()
.. autoclass:: walnats.serializers.DataclassSerializer()
.. autoclass:: walnats.serializers.DatetimeSerializer()
.. autoclass:: walnats.serializers.MarshmallowSerializer()
.. autoclass:: walnats.serializers.PrimitiveSerializer()
.. autoclass:: walnats.serializers.ProtobufSerializer()
.. autoclass:: walnats.serializers.PydanticSerializer()
```

## Optional

Optional serializers are the ones that aren't automatically detected, so you have to specify them explicitly to use.

```{eval-rst}
.. autoclass:: walnats.serializers.MessagePackSerializer()
```

## Wrappers

Wrappers are serializers that wrap another serializer to modify its output in some way.

```{eval-rst}
.. autoclass:: walnats.serializers.FernetSerializer
.. autoclass:: walnats.serializers.GZipSerializer
.. autoclass:: walnats.serializers.HMACSerializer
```
