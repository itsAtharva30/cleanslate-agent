# CleanSlate

An agent that turns dirty Excel datasets into clean, color-coded, print-ready
workbooks, with a full change log and insights.

> **Status:** early development. Stage 0 (foundation) and Stage 1 (ingest and
> original protection) are done. The cleaning pipeline is not built yet. See
> [docs/progress.md](docs/progress.md).

## Planned workflow

Upload a messy `.xlsx` file, then detect anomalies, propose fixes, apply them
to a **copy**, and receive a clean workbook containing: a cover sheet, the
original data, the cleaned data (color-coded), an anomaly report, a change log,
and insights.

## Design principles

- The original file is never modified. All work happens on a copy in a
  per-run folder, verified with a SHA-256 hash.
- The LLM decides and explains. Plain Python code touches the data. The LLM
  returns structured JSON, never edits cells directly.
- Every change is logged (cell, column, before, after, rule, reason).
- Humans approve fixes before they are applied.
- Full datasets are never sent to an LLM. Only profiles and small samples are
  sent, with PII masked.

## Color legend

| Color  | Meaning                                    |
|--------|--------------------------------------------|
| Red    | Invalid or impossible value, left unfixed  |
| Orange | Outlier, kept                              |
| Yellow | Auto-corrected (format, case, spacing)     |
| Blue   | Imputed value                              |
| Purple | Duplicate removed or merged                |
| None   | Clean                                      |

## Setup (Windows PowerShell)

```powershell
git clone https://github.com/itsAtharva30/cleanslate-agent.git
cd cleanslate-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Using it (Stage 1: ingest)

Stage 1 validates a workbook, copies it into a new run folder, verifies the
copy, reads the copy and records a manifest. It does not clean anything yet.

```powershell
python -m cleanslate ingest path\to\file.xlsx
```

Each run creates `data\runs\<UTC timestamp>_<id>\` containing
`input\<your file>` (the verified copy) and `manifest.json`. Use `--runs-dir`
to choose another folder. The original file is never modified: it is hashed
before the copy and again at the end, and the run fails if the hash changed.

The manifest records names, SHA-256 hashes, counts, library versions and
warnings (hidden sheets, merged cells, formulas). It never contains cell
contents.

Exit codes: `0` success, `1` unusable input file, `2` wrong usage, `3` a safety
check failed (the original changed or the copy differs).

The package also declares a `cleanslate` console command. Some Windows setups
block the launcher it generates (Application Control), so `python -m
cleanslate` is the form that always works.

## Sample data

```powershell
python scripts/make_messy_sample.py
```

Writes `data\samples\messy_orders.xlsx`, a deliberately dirty workbook, and
`messy_orders.truth.json`, a ground-truth file listing every planted problem
(sheet, row, column, color category and kind). Both are git-ignored. The data
is repeatable for a given `--seed`, but the `.xlsx` bytes are not, because
Excel files embed their save time, so compare cell values and never file
hashes.

## Development

```powershell
python -m pytest -v            # run tests
python -m ruff check .         # lint
python -m ruff format .        # format
```

Requires Python 3.11 or newer.

## Roadmap

0 Foundation | 1 Ingest and original protection | 2 Profiling |
3 Anomaly detection | 4 Cleaning engine and change log |
5 Color-coded, print-ready Excel output | 6 LLM reasoning layer |
7 Review UI and download | 8 Insights | 9 Evaluation, hardening, release

## License

MIT