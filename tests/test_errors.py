from __future__ import annotations

import pytest
from nats.js.errors import BadRequestError, ServerError

from walnats._errors import convert_stream_errors


@pytest.mark.parametrize('exists_ok', [True, False])
@pytest.mark.parametrize('to_raise', [
    Exception,
    BaseException,
    ValueError,
    BadRequestError,
    ServerError,
])
def test_convert_stream_errors__passthrough(
    exists_ok: bool,
    to_raise: type[Exception],
) -> None:
    with pytest.raises(to_raise):
        with convert_stream_errors(exists_ok=exists_ok):
            raise to_raise
