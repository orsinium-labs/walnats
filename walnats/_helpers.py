from __future__ import annotations

from typing import Any

from ._actors import Actor, Actors


async def run_actors(*actors: Actor, **kwargs: Any) -> None:
    """A little helper to create Actors registry, register it, and listen for events.

    It's better to use the full form if you want to pass arguments into ``listen``.
    It will be 4 lines of code instead of 1 but then the arguments you pass are type-safe.
    This helper exists for a quick start when you didn't get to fine-grained tuning
    of how your actors behave.

            actors = Actors(actor1, actor2)
            async with actors.connect() as conn:
                await conn.register()
                await conn.listen(**kwargs)

    """
    registry = Actors(*actors)
    async with registry.connect() as conn:
        await conn.register()
        await conn.listen(**kwargs)
