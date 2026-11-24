# CleanSlate — Progress
**Current stage:** 0 — Foundation | **Status:** done
**Last updated:** 2026-11-11

## Completed stages
- Stage 0: Foundation | tag v0.0-stage0 (merge commit 28ee265, PR #1) |
  key files: pyproject.toml, src/cleanslate/__init__.py, tests/test_smoke.py,
  .env.example, .gitignore, README.md, docs/ |
  learned: venv and editable installs, pyproject.toml, src layout, pytest
  basics, ruff lint/format, git ignore rule ordering, secrets hygiene,
  branch / PR / merge / annotated tag workflow

## Current stage checklist
- [x] Stage 0 complete. Stage 1 (Ingest and original protection) not started.

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
- Python 3.14.4 is very new. Compatibility of pandas, Pydantic, openpyxl,
  XlsxWriter and Streamlit must be verified at install time in Stages 1, 6
  and 7. Fallback: install Python 3.12 alongside and rebuild the venv.
- Repo folder is nested on disk (cleanslate-agent\cleanslate-agent). Cosmetic
  only; left as is to avoid risk.
- The v0.0-stage0 tag was created before this progress update, so the tagged
  progress.md still says "in progress". Harmless; later tags will include
  the updated file.

## Backlog (priority: H/M/L)
- H: Stage 1 opens with a generator script for a deterministic messy sample
  .xlsx with known injected errors (ground truth for tests and Stage 9).
- H: Verify library compatibility with Python 3.14 when installing pandas.
- M: Decide openpyxl vs XlsxWriter at Stage 5 (reading vs styled writing).
- M: GitHub Actions CI running pytest and ruff on every PR.
- M: pre-commit hooks for ruff.
- L: Switch environment tooling to uv.
- L: Stricter ruff rules (docstrings, type annotations) and type checking.
- L: Disable the git pager globally (core.pager) if it keeps getting in the way.

## Next up
- Stage 1: Ingest and original protection (branch stage-1-ingest).