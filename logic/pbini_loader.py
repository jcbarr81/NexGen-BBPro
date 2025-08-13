from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def load_pbini(path: str | Path) -> Dict[str, Dict[str, Any]]:
    """Load a PB.INI style configuration file.

    The file format uses ``key=value`` pairs and allows comments beginning
    with ``;``. Section headers are surrounded by square brackets like
    ``[Section]``. Values are converted to ``int`` when possible and otherwise
    left as strings.
    """
    path = Path(path)
    config: Dict[str, Dict[str, Any]] = {}
    current_section: str | None = None

    with path.open() as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith(";"):
                continue

            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                config.setdefault(current_section, {})
                continue

            # Remove inline comments
            if ";" in line:
                line = line.split(";", 1)[0].strip()
            if not line or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Convert numeric values when possible
            try:
                value_converted: Any = int(value)
            except ValueError:
                try:
                    value_converted = float(value)
                except ValueError:
                    value_converted = value

            section_dict = config.setdefault(current_section or "", {})
            section_dict[key] = value_converted

    return config


__all__ = ["load_pbini"]
