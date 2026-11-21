"""Command-line interface for CleanSlate.

    python -m cleanslate ingest <file.xlsx> [--runs-dir DIR]

Exit codes:
    0  success
    1  the input file is unusable
    2  wrong command-line usage (argparse's own convention)
    3  a safety check failed: the original changed or the copy differs
Any other exception is a bug and shows its traceback.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from cleanslate import __version__
from cleanslate.errors import CleanSlateError, IntegrityError
from cleanslate.ingest import ingest

# Anchored to the repo root (src/cleanslate/cli.py -> parents[2]), so the default
# does not depend on the folder you run the command from. This holds for an
# editable install of this repo, which is how the project is developed.
DEFAULT_RUNS_ROOT = Path(__file__).resolve().parents[2] / "data" / "runs"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INTEGRITY = 3


def _ingest_command(args: argparse.Namespace) -> int:
    try:
        result = ingest(args.file, args.runs_dir)
    except CleanSlateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INTEGRITY if isinstance(exc, IntegrityError) else EXIT_ERROR

    manifest = result.manifest
    print(f"Run folder: {result.run_dir.resolve()}")
    print(f"Manifest:   {result.manifest_path.resolve()}")
    print(f"Sheets:     {len(manifest.sheets)}")
    print(f"Original:   unchanged (SHA-256 {manifest.original_sha256_after})")
    print(f"Warnings:   {len(manifest.warnings)}")
    for warning in manifest.warnings:
        print(f"  - {warning}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleanslate",
        description="Turn dirty Excel datasets into clean, color-coded workbooks.",
    )
    parser.add_argument(
        "--version", action="version", version=f"cleanslate {__version__}"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    ingest_parser = commands.add_parser(
        "ingest",
        help="validate a workbook, copy it into a new run folder, record a manifest",
        description=(
            "Validate an .xlsx file, copy it into a new run folder, read the copy "
            "and write manifest.json. The original file is never modified."
        ),
    )
    ingest_parser.add_argument("file", type=Path, help="path to the .xlsx file")
    ingest_parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_ROOT,
        help="folder that holds run folders (default: <repo>/data/runs)",
    )
    ingest_parser.set_defaults(handler=_ingest_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)
