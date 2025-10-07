Versioning
===========

- Version file: `VERSION` at the repo root (format: `MAJOR.MINOR.PATCH`).
- Initial version: `1.0.0`.
- On commit: a pre-commit hook bumps the patch number automatically if `VERSION` isn’t already staged.

How it works
- Hook location: `.githooks/pre-commit` (repo-local and tracked).
- Git is configured to use this hooks path: `git config core.hooksPath .githooks`.
- The hook:
  - Runs `pytest -q` and prints a warning if tests fail (does not block).
  - If `VERSION` isn’t staged, runs `scripts/bump_version.py` to increment the patch, stages `VERSION`, and aborts the commit with a message. Re-run the commit to include the bumped version. On the second attempt the hook detects `VERSION` is staged and does not bump again.

Manual bumping
- You can bump manually with: `python scripts/bump_version.py --part [major|minor|patch]`.
- The script prints the new version and writes it to `VERSION`.

Notes
- On Linux/macOS you may need to ensure the hook is executable: `chmod +x .githooks/pre-commit`.
- If you ever reset hooks: `git config core.hooksPath .githooks` to re-enable repo-local hooks.
