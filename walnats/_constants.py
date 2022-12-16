from typing import Final

import nats.js


# Header to use to specify inbox for emitted messages when using request/reply.
HEADER_REPLY: Final = 'Walnats-Reply'

# Header that Nats uses for message deduplication.
HEADER_ID: Final = nats.js.api.Header.MSG_ID.value

# Header for trace ID for distributed tracing.
HEADER_TRACE: Final = 'Walnats-Trace'

# Header for the timestamp until which the message has been delayed
# (in UTC, in seconds, as float).
HEADER_DELAY = 'Walnats-Delay'
