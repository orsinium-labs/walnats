# Integrations

Looking for an integration with a specific service or tool? There is a good chance walnats already provides it out of the box.

1. [alloy](http://alloytools.org/): [Verification](./alloy)
1. [asyncapi](https://www.asyncapi.com/): {py:meth}`walnats.Services.get_async_api`.
1. [cloudevents](https://github.com/cloudevents/spec): {py:class}`walnats.CloudEvent`.
1. [cryptography](https://cryptography.io/en/latest/): {py:class}`walnats.serializers.FernetSerializer`.
1. [d2](https://github.com/terrastruct/d2): {py:meth}`walnats.Services.get_d2`.
1. [datadog](https://www.datadoghq.com/): {py:class}`walnats.middlewares.StatsdMiddleware`.
1. [event storming](https://en.wikipedia.org/wiki/Event_storming): {py:meth}`walnats.Services.get_d2`.
1. [google cloud trace](https://cloud.google.com/trace/docs/zipkin): {py:class}`walnats.middlewares.ZipkinMiddleware`.
1. [marshmallow](https://github.com/marshmallow-code/marshmallow): {py:class}`walnats.serializers.MarshmallowSerializer`.
1. [messagepack](https://msgpack.org/index.html) (msgpack): {py:class}`walnats.serializers.MessagePackSerializer`.
1. [prometheus](https://prometheus.io/): {py:class}`walnats.middlewares.PrometheusMiddleware`.
1. [protobuf](https://developers.google.com/protocol-buffers) (protocol buffers): {py:class}`walnats.serializers.ProtobufSerializer`.
1. [pydantic](https://pydantic-docs.helpmanual.io/): {py:class}`walnats.serializers.PydanticSerializer`.
1. [sentry](https://sentry.io/welcome/): {py:class}`walnats.middlewares.SentryMiddleware`.
1. [statsd](https://github.com/statsd/statsd): {py:class}`walnats.middlewares.StatsdMiddleware`.
1. [zipkin](https://zipkin.io/): {py:class}`walnats.middlewares.ZipkinMiddleware`.
