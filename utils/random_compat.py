"""Compatibility helpers for random seeding.

PyPy enforces hashing of seeds passed to ``random.Random`` at object creation
which breaks tests that create ``MockRandom`` subclasses with predefined
sequences.  CPython is more permissive, so provide a small shim that converts
common unhashable seeds (lists, tuples, other iterables) into hashable values
before delegating to the original constructor.
"""
from __future__ import annotations

import random
from typing import Any


_PATCH_ATTR = "_playbalance_seed_patch"

def _hashable(value: Any) -> Any:
    try:
        hash(value)
    except TypeError:
        if isinstance(value, (list, tuple)):
            return tuple(_hashable(v) for v in value)
        try:
            return tuple(value)  # type: ignore[arg-type]
        except TypeError:
            return repr(value)
    return value


def ensure_hashable_random_new() -> None:
    """Patch ``random.Random.__new__`` to coerce unhashable seeds."""

    if getattr(random.Random, _PATCH_ATTR, False):
        return

    original_new = random.Random.__new__

    def _patched_new(cls, *args, **kwargs):
        if args:
            seed = _hashable(args[0])
            args = (seed,) + args[1:]
        return original_new(cls, *args, **kwargs)

    random.Random.__new__ = _patched_new  # type: ignore[assignment]
    setattr(random.Random, _PATCH_ATTR, True)
