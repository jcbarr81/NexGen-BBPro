"""Build an executable for NexGen-BBPro using PyInstaller."""

from __future__ import annotations

import os
import PyInstaller.__main__


def main() -> None:
    """Run PyInstaller to create a standalone executable."""
    data_dirs = ["data", "logo", "assets", "images"]
    params = ["main.py", "--onefile", "--name", "NexGen-BBPro"]
    for d in data_dirs:
        params += ["--add-data", f"{d}{os.pathsep}{d}"]
    PyInstaller.__main__.run(params)


if __name__ == "__main__":
    main()
