import logging
import random
from collections.abc import Sequence

logger = logging.getLogger(__name__)


class RandomSelector:
    """Samples items without replacement, optionally with a fixed seed."""

    def __init__(self, seed: int | None = None) -> None:
        """Create a selector; pass ``seed`` for reproducible runs."""
        self._rng = random.Random(seed)

    def pick[T](self, items: Sequence[T], count: int) -> list[T]:
        """Return ``count`` random items, or all of them if fewer exist."""
        if count >= len(items):
            if count > len(items):
                logger.warning("Requested %d items but only %d available", count, len(items))
            return list(items)
        return self._rng.sample(list(items), count)

    def pick_between[T](self, items: Sequence[T], low: int, high: int) -> list[T]:
        """Pick a random number of items in ``[low, high]`` (clamped)."""
        return self.pick(items, self._rng.randint(low, high))
