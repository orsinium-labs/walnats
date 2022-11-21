import pydantic

import walnats


class CounterModel(pydantic.BaseModel):
    value: int


COUNTER = walnats.Event('counter', CounterModel)
