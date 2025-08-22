"""A minimal bcrypt-compatible interface for testing.

This stub implements a tiny subset of the :mod:`bcrypt` API used in the
unit tests.  It is *not* a secure implementation and should only be used
for local testing when the real dependency is unavailable.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Any

__all__ = ["gensalt", "hashpw", "checkpw"]


def gensalt() -> bytes:
    """Return a random 16-byte salt."""
    return os.urandom(16)


def hashpw(password: bytes, salt: bytes) -> bytes:
    """Return a hashed password using SHA-256.

    The result is base64 encoded so it resembles the real bcrypt output and
    can be stored as text if desired.
    """

    digest = hashlib.sha256(salt + password).digest()
    return base64.b64encode(salt + digest)


def checkpw(password: bytes, hashed: bytes) -> bool:
    """Verify a password against a hashed value."""
    data = base64.b64decode(hashed)
    salt, digest = data[:16], data[16:]
    expected = hashlib.sha256(salt + password).digest()
    return hmac.compare_digest(digest, expected)
