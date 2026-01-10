from __future__ import annotations

import os
import warnings

_ENV_VAR = "PB_ALLOW_LEGACY_ENGINE"


def legacy_enabled() -> bool:
    return str(os.getenv(_ENV_VAR, "")).strip().lower() in {"1", "true", "yes", "on"}


def warn_legacy_disabled(context: str) -> None:
    if legacy_enabled():
        return
    warnings.warn(
        f"{context} is archived. Set {_ENV_VAR}=1 to run it intentionally.",
        RuntimeWarning,
        stacklevel=2,
    )


def require_legacy_enabled(context: str) -> None:
    if legacy_enabled():
        return
    raise RuntimeError(
        f"{context} is archived. Set {_ENV_VAR}=1 to run it intentionally."
    )
