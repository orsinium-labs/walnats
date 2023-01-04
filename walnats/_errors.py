from __future__ import annotations

from contextlib import contextmanager

from nats.js.errors import BadRequestError, ServerError


JS_STREAM_EXISTS = 10058
JS_STREAM_CONFIG = 10052
JS_CONSUMER_EXISTS = 10013


class StreamExistsError(BadRequestError):
    """Stream name already in use with a different configuration.

    Possible causes:

    * You tried to register two events with the same name. The event name must be unique.
    * You changed the event configuration but called `register(update=False)`.

    """


class StreamConfigError(BadRequestError):
    """Stream configuration cannot be updated.

    Possible causes:

    * You specified an invalid value for a config option.
    * You tried to change a configuration option that cannot be changed.

    """


class ConsumerExistsError(BadRequestError):
    """Consumer name already in use.

    Possible causes:

    * You tried to register two actors with the same name. The actor name must be unique.
    * You changed the actor configuration but called `register(update=False)`.
    * You changed in the actor configuration an option that cannot be updated
      for an existing consumer.

    """


@contextmanager
def convert_errors(exists_ok: bool = False):
    """Convert some of the nats.py errors into walnats errors.

    Args:
        exists_ok: do not raise an exception if stream/consumer already exists.
    """
    try:
        yield
    except BadRequestError as exc:
        if exc.err_code == JS_STREAM_EXISTS:
            if exists_ok:
                return
            raise StreamExistsError(
                code=400,
                err_code=exc.err_code,
                description=exc.description,
                stream=exc.stream,
                seq=exc.seq,
            )
        if exc.err_code == JS_CONSUMER_EXISTS:
            if exists_ok:
                return
            raise ConsumerExistsError(
                code=400,
                err_code=exc.err_code,
                description=exc.description,
                stream=exc.stream,
                seq=exc.seq,
            )
        raise
    except ServerError as exc:
        if exc.err_code == JS_STREAM_CONFIG:
            raise StreamConfigError(
                code=400,
                err_code=exc.err_code,
                description=exc.description,
                stream=exc.stream,
                seq=exc.seq,
            )
