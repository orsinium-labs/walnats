# Middlewares

## Custom middlewares

```{eval-rst}
.. autoclass:: walnats.middlewares.Middleware
    :members:
.. autoclass:: walnats.types.Context
.. autoclass:: walnats.types.ErrorContext
.. autoclass:: walnats.types.OkContext
```

## Integrations

Integrations with third-party services to provide observability for running actors.

```{eval-rst}
.. autoclass:: walnats.middlewares.PrometheusMiddleware
.. autoclass:: walnats.middlewares.SentryMiddleware
.. autoclass:: walnats.middlewares.StatsdMiddleware
.. autoclass:: walnats.middlewares.ZipkinMiddleware
```

## Misc

Miscellaneous middlewares that don't depend on third-party packages or services.

```{eval-rst}
.. autoclass:: walnats.middlewares.CurrentContextMiddleware
.. autoclass:: walnats.middlewares.ExtraLogMiddleware
.. autoclass:: walnats.middlewares.TextLogMiddleware
```

## Wrappers

Wrappers are middlewares that wrap another middleware, usually to provide some kind of flow control.

```{eval-rst}
.. autoclass:: walnats.middlewares.ErrorThresholdMiddleware()
.. autoclass:: walnats.middlewares.FrequencyMiddleware()
```
