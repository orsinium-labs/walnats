"""A collection of useful decorators for handlers.

While middlewares help with observability without any effect on the handler execution,
decorators are great for flow control. They can filter, rate-limit, suppress, and retry
handlers.
"""
from ._filter_time import filter_time
from ._rate_limit import rate_limit
from ._require import require
from ._suppress import suppress


__all__ = [
    'filter_time',
    'rate_limit',
    'require',
    'suppress',
]
