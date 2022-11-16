from random import choice
from string import ascii_letters


def get_random_name() -> str:
    return ''.join(choice(ascii_letters) for _ in range(20))
