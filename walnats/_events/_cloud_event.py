from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True)
class CloudEvent:
    """Event metadata as described in CloudEvents spec.

    The spec: https://github.com/cloudevents/spec/blob/v1.0/spec.md
    """
    # required
    id: str
    source: str
    type: str
    specversion: str = '1.0'

    # optional
    datacontenttype: str | None = None
    dataschema: str | None = None
    subject: str | None = None
    time: datetime | None = None

    # extensions
    dataref: str | None = None
    partitionkey: str | None = None
    sampledrate: int | None = None
    sequence: str | None = None
    traceparent: str | None = None
    tracestate: str | None = None

    def as_dict(self) -> dict[str, str | int]:
        """Represent the metadata as a JSON-friendly dict.
        """
        result = {k: v for k, v in asdict(self).items() if v is not None}
        if self.time is not None:
            result['time'] = f'{self.time.isoformat()}Z'
        return result

    def as_headers(self) -> dict[str, str]:
        """Produce Nats-compatible headers from the metadata.

        The headers and their format are described in the WIP spec
        for Nats binding.

        The spec: https://github.com/cloudevents/spec/blob/main/cloudevents/bindings/nats-protocol-binding.md
        """  # noqa: E501
        return {f'ce-{k}': str(v) for k, v in self.as_dict().items()}
