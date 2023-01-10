from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class Limits:
    """Stream configuration options limiting the Stream size.

    When any of the limits is reached, Nats will drop old messages to fit into the limit.

    https://docs.nats.io/nats-concepts/jetstream/streams#configuration
    """

    age: float | None = None
    """Maximum age of any message in the Stream in seconds."""

    consumers: int | None = None
    """How many Consumers can be defined for a given Stream."""

    messages: int | None = None
    """How many messages may be in a Stream."""

    bytes: int | None = None
    """How many bytes the Stream may contain."""

    message_size: int | None = None
    """The largest message that will be accepted by the Stream."""

    def evolve(self, **kwargs: float | None) -> Limits:
        """Create a copy of Limits with the given fields changed.
        """
        return dataclasses.replace(self, **kwargs)
