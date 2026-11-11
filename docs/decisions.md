# Decisions log

| Date | Decision | Why | Alternatives rejected |
|------|----------|-----|-----------------------|
| 2026-11-11 | Repo created on GitHub first, then cloned | GitHub makes the initial commit on main, so pull requests work from the start | git init locally, then add a remote |
| 2026-11-11 | One branch per stage, merged by PR, tagged | Keeps main always working; clean history; mirrors professional workflow | Committing straight to main |
| 2026-11-11 | venv in .venv inside the repo | Built in, teaches what a virtual environment is | conda, uv (uv is in the backlog), poetry |
| 2026-11-11 | pyproject.toml for metadata and dependencies | Modern standard; also holds pytest and ruff settings | requirements.txt only |
| 2026-11-11 | src/ layout with editable install | Prevents tests importing uninstalled code | Flat layout |
| 2026-11-11 | Version defined once in pyproject.toml, read via importlib.metadata | Single source of truth | Hard-coding __version__ in two places |
| 2026-11-11 | ruff for linting and formatting | One fast tool, one config | black + flake8 + isort |
| 2026-11-11 | Add runtime libraries only when a stage needs them | Understand why each dependency exists | Installing the whole stack in Stage 0 |
| 2026-11-11 | data/ ignored by git; synthetic samples live in tests/ | Real datasets may contain PII | Committing sample data in data/ |
| 2026-11-11 | .env.example tracked, .env ignored | API key arrives in Stage 6; secrets must never reach git | Committing a key, or no template |
