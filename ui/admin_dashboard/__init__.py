"""Admin dashboard package scaffolding.

This package currently re-exports the legacy monolithic dashboard while
new modular components are built out. Once migrations complete, the
shim in `legacy_entry` will be retired and this package will expose the
new implementation directly.
"""

from .legacy_entry import *  # noqa: F401,F403

__all__ = [name for name in globals() if not name.startswith("_")]
