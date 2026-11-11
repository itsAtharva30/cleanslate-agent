# CleanSlate

An agent that turns dirty Excel datasets into clean, color-coded, print-ready
workbooks, with a full change log and insights.

> **Status:** early development. Stage 0 (foundation) is in progress. The
> pipeline itself is not built yet. See [docs/progress.md](docs/progress.md).

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
git clone https://github.com/YOUR-GITHUB-USERNAME/cleanslate-agent.git
cd cleanslate-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Development

```powershell
pytest -v            # run tests
ruff check .         # lint
ruff format .        # format
```

Requires Python 3.11 or newer.

## Roadmap

0 Foundation | 1 Ingest and original protection | 2 Profiling |
3 Anomaly detection | 4 Cleaning engine and change log |
5 Color-coded, print-ready Excel output | 6 LLM reasoning layer |
7 Review UI and download | 8 Insights | 9 Evaluation, hardening, release

## License

MIT