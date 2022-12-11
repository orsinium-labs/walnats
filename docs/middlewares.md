# Middlewares

## Custom middlewares

```{eval-rst}
.. autoclass:: walnats.middlewares.Middleware
    :members:
.. autoclass:: walnats.types.Context
.. autoclass:: walnats.types.ErrorContext
.. autoclass:: walnats.types.OkContext
```

## Wrappers

```{eval-rst}
.. autoclass:: walnats.middlewares.ErrorThresholdMiddleware()
.. autoclass:: walnats.middlewares.FrequencyMiddleware()
```

## Integrations

```{eval-rst}
.. autoclass:: walnats.middlewares.ExtraLogMiddleware
.. autoclass:: walnats.middlewares.PrometheusMiddleware
.. autoclass:: walnats.middlewares.SentryMiddleware
.. autoclass:: walnats.middlewares.StatsdMiddleware
.. autoclass:: walnats.middlewares.ZipkinMiddleware
```
