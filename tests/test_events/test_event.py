import walnats


def test_limits__evolve():
    lim1 = walnats.Limits(age=10, messages=20)
    lim2 = lim1.evolve(age=15)
    assert lim1 == walnats.Limits(age=10, messages=20)
    assert lim2 == walnats.Limits(age=15, messages=20)
