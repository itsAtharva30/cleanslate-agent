# CleanSlate — Progress
**Current stage:** 0 — Foundation | **Status:** in progress
**Last updated:** 2026-11-11

## Completed stages
- None yet.

## Current stage checklist
- [x] Tools verified (Python 3.14.4, git 2.53, pip 26.0.1)
- [x] GitHub repo created and cloned
- [x] Branch stage-0-foundation created
- [x] Virtual environment (.venv) created and activated
- [x] pyproject.toml written
- [x] src/cleanslate package skeleton, editable install
- [x] Smoke tests passing (pytest)
- [x] Ruff configured; code lint-clean and formatted
- [x] Secrets hygiene: .env.example, data/ ignore rules
- [ ] README, progress.md, decisions.md written
- [ ] Branch pushed, pull request opened and merged
- [ ] Tag v0.0-stage0 created

## Decisions log
See docs/decisions.md for the full log with reasons and rejected alternatives.

## Repo structure (current)
    cleanslate-agent/
    ├── .env.example
    ├── .gitignore
    ├── LICENSE
    ├── README.md
    ├── pyproject.toml
    ├── data/.gitkeep
    ├── docs/
    │   ├── decisions.md
    │   └── progress.md
    ├── src/cleanslate/__init__.py
    └── tests/test_smoke.py

## Known issues
- Python 3.14 is very new. Compatibility of pandas, Pydantic, openpyxl,
  XlsxWriter and Streamlit must be verified at install time in Stages 1, 6
  and 7. Fallback: install Python 3.12 alongside.

## Backlog (priority: H/M/L)
- H: Stage 1 opens with a generator script for a deterministic messy sample
  .xlsx with known injected errors (ground truth for tests and Stage 9).
- H: Verify library compatibility with Python 3.14 when installing pandas.
- M: Decide openpyxl vs XlsxWriter at Stage 5 (reading vs styled writing).
- M: GitHub Actions CI running pytest and ruff on every PR.
- M: pre-commit hooks for ruff.
- L: Switch environment tooling to uv.
- L: Stricter ruff rules (docstrings, type annotations) and type checking.

## Next up
- Finish Stage 0 (docs, PR, merge, tag), then Stage 1: Ingest and original
  protection.