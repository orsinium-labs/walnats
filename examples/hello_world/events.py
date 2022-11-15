import pydantic

import walnats


class CounterModel(pydantic.BaseModel):
    value: int


COUNTER_EVENT = walnats.Event('counter', CounterModel)
