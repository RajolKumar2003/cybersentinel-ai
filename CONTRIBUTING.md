# Contributing

This is a personal portfolio project, but it's structured to accept
contributions like a real one.

1. Fork and branch from `main`.
2. `pip install -r backend/requirements.txt -r frontend/requirements.txt`
3. Run `ruff check .`, `black --check .`, and `pytest` before opening a PR —
   CI runs the same checks and will fail the build otherwise.
4. Keep functions typed; `mypy` runs in CI on `backend/app`.
5. No secrets, credentials, or real network data in commits — see `SECURITY.md`.
6. Describe what you tested (unit / integration / manual) in the PR body.
