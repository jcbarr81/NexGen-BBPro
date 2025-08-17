"""Reusable OpenAI client configured via ``config.ini``.

Reads the API key from the ``[OpenAIkey]`` section of ``config.ini`` and
creates a singleton ``OpenAI`` client that can be imported anywhere in the
project. If the :mod:`openai` package is not installed or a key is missing, the
``client`` variable will be ``None``.
"""
from __future__ import annotations

import configparser
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - gracefully handle missing dependency
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


def _read_api_key() -> Optional[str]:
    """Return the OpenAI API key from ``config.ini`` if available."""
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "config.ini"
    parser = configparser.ConfigParser()
    try:
        parser.read(config_path)
    except configparser.Error:
        parser = None

    if parser:
        # Typical ``key=value`` entries
        for opt in ("key", "api_key", "OPENAI_API_KEY"):
            if parser.has_option("OpenAIkey", opt):
                return parser.get("OpenAIkey", opt)

        # Handle a section containing only the raw key on following lines
        if "OpenAIkey" in parser and not parser["OpenAIkey"]:
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
            except OSError:
                return None
            inside = False
            key_lines: list[str] = []
            for line in lines:
                if line.strip() == "[OpenAIkey]":
                    inside = True
                    continue
                if inside:
                    if line.startswith("["):
                        break
                    key_lines.append(line.strip())
            if key_lines:
                return "".join(key_lines).strip()

    # Fallback manual parsing when ``ConfigParser`` fails entirely
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    inside = False
    key_lines: list[str] = []
    for line in lines:
        if line.strip() == "[OpenAIkey]":
            inside = True
            continue
        if inside:
            if line.startswith("["):
                break
            key_lines.append(line.strip())
    if key_lines:
        return "".join(key_lines).strip()
    return None


_api_key = _read_api_key()

# Exposed, reusable OpenAI client instance. ``None`` if not configured.
client: Optional[OpenAI]
if OpenAI is not None and _api_key:
    client = OpenAI(api_key=_api_key)
else:  # pragma: no cover - executed when dependency missing
    client = None

__all__ = ["client"]
