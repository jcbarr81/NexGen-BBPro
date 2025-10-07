#!/usr/bin/env python3
"""
Utility to bump the patch number in the repository's VERSION file.

Version format: MAJOR.MINOR.PATCH (e.g., 1.0.0)

Default behavior: bump patch by 1.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def read_version() -> tuple[int, int, int]:
    if not VERSION_FILE.exists():
        return (1, 0, 0)
    text = VERSION_FILE.read_text(encoding="utf-8").strip()
    m = VERSION_RE.match(text)
    if not m:
        raise ValueError(f"Invalid version string in {VERSION_FILE}: '{text}'")
    return tuple(int(g) for g in m.groups())  # type: ignore[return-value]


def write_version(major: int, minor: int, patch: int) -> str:
    version = f"{major}.{minor}.{patch}"
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    return version


def bump(semver: tuple[int, int, int], part: str) -> tuple[int, int, int]:
    major, minor, patch = semver
    if part == "major":
        return (major + 1, 0, 0)
    if part == "minor":
        return (major, minor + 1, 0)
    # default: patch
    return (major, minor, patch + 1)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Bump VERSION file")
    parser.add_argument(
        "--part",
        choices=["major", "minor", "patch"],
        default="patch",
        help="Which part of the version to bump (default: patch)",
    )
    args = parser.parse_args(argv)

    current = read_version()
    new_version = bump(current, args.part)
    result = write_version(*new_version)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

