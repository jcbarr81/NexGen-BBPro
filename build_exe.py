"""Build an executable for NexGen-BBPro using PyInstaller."""

from __future__ import annotations

import os
import PyInstaller.__main__


def main() -> None:
    """Run PyInstaller to create a standalone executable."""
    data_dirs = ["data", "logo", "assets", "images"]
    icon_path = os.path.join("logo", "UBL.ico")
    # --noconsole prevents a console window from appearing when the app runs
    params = [
        "main.py",
        "--onefile",
        "--name",
        "NexGen-BBPro",
        "--noconsole",
        "--icon",
        icon_path,
    ]
    for d in data_dirs:
        params += ["--add-data", f"{d}{os.pathsep}{d}"]
    PyInstaller.__main__.run(params)


if __name__ == "__main__":
    main()
