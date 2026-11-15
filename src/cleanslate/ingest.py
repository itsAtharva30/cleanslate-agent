"""Stage 1: validate the input file, then copy, read and record it.

validate_input, read_workbook and ingest (which chains them) live here.
"""

import platform
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl import load_workbook

from cleanslate import __version__
from cleanslate.errors import (
    CorruptWorkbookError,
    EmptyFileError,
    InputError,
    InputNotFoundError,
    OriginalModifiedError,
    UnsupportedFileTypeError,
)
from cleanslate.hashing import sha256_file
from cleanslate.models import RunManifest, SheetInfo
from cleanslate.runs import create_run

SUPPORTED_SUFFIX = ".xlsx"
MANIFEST_FILENAME = "manifest.json"


def validate_input(path: str | Path) -> Path:
    """Check that path is a usable .xlsx file and return its resolved path.

    Raises a specific InputError subclass for each way the file can be unusable.
    The file is only read, never modified.
    """
    p = Path(path)

    if not p.is_file():
        raise InputNotFoundError(f"Not an existing file: {p}")

    if p.name.startswith("~$"):
        raise InputError(
            f"{p.name} is an Excel lock file (created while a workbook is open), "
            "not the workbook itself. Close Excel and pass the real .xlsx file."
        )

    if p.suffix.lower() != SUPPORTED_SUFFIX:
        raise UnsupportedFileTypeError(
            f"Only {SUPPORTED_SUFFIX} files are supported, got '{p.suffix}': {p}"
        )

    if p.stat().st_size == 0:
        raise EmptyFileError(f"File is empty (0 bytes): {p}")

    try:
        workbook = load_workbook(p, read_only=True)
    except Exception as exc:
        raise CorruptWorkbookError(
            f"Cannot open as an Excel workbook (corrupt, or password-protected?): {p}"
        ) from exc
    workbook.close()

    return p.resolve()


@dataclass(frozen=True)
class WorkbookData:
    """Raw sheet values plus structural facts, read from the copy."""

    sheets: dict[str, pd.DataFrame]
    sheet_infos: list[SheetInfo]
    warnings: list[str]


def read_workbook(path: str | Path) -> WorkbookData:
    """Read every sheet of the workbook at path as raw data, with hazard warnings.

    Call this on the COPY inside the run folder, never on the original. Values are
    read with header=None and dtype=object, so nothing is guessed or converted.
    Hidden sheets are still read, and each hazard is reported as a warning.
    Warnings hold sheet names and counts only, never cell contents.
    """
    path = Path(path)
    frames = pd.read_excel(path, sheet_name=None, header=None, dtype=object)

    infos: list[SheetInfo] = []
    warnings: list[str] = []
    # Full load, not read_only: read-only worksheets have no merged_cells.
    workbook = load_workbook(path)
    try:
        for ws in workbook.worksheets:
            frame = frames[ws.title]
            merged = len(ws.merged_cells.ranges)
            formulas = sum(
                1 for row in ws.iter_rows() for cell in row if cell.data_type == "f"
            )
            infos.append(
                SheetInfo(
                    name=ws.title,
                    state=ws.sheet_state,
                    n_rows=frame.shape[0],
                    n_cols=frame.shape[1],
                    merged_ranges=merged,
                    formula_cells=formulas,
                )
            )
            if ws.sheet_state == "hidden":
                warnings.append(f"Hidden sheet: '{ws.title}'")
            elif ws.sheet_state == "veryHidden":
                warnings.append(f"Very hidden sheet: '{ws.title}'")
            if merged:
                warnings.append(
                    f"Merged cells in '{ws.title}': {merged} range(s). "
                    "Only the top-left cell of each range holds a value."
                )
            if formulas:
                warnings.append(
                    f"Formulas in '{ws.title}': {formulas} cell(s). A formula "
                    "cell reads as empty when the file holds no saved result "
                    "(for example, a file written by a script)."
                )
    finally:
        workbook.close()

    return WorkbookData(sheets=frames, sheet_infos=infos, warnings=warnings)


def verify_original_untouched(source: str | Path, expected_sha256: str) -> str:
    """Re-hash the original and raise OriginalModifiedError if it changed.

    Returns the fresh hash, which the manifest records as original_sha256_after.
    """
    actual = sha256_file(source)
    if actual != expected_sha256:
        raise OriginalModifiedError(
            f"The original file changed during the run: {source} "
            f"(before {expected_sha256}, after {actual})."
        )
    return actual


@dataclass(frozen=True)
class IngestResult:
    """Everything Stage 1 produces."""

    manifest: RunManifest
    run_dir: Path
    manifest_path: Path
    sheets: dict[str, pd.DataFrame]


def ingest(
    path: str | Path,
    runs_root: str | Path,
    *,
    now: datetime | None = None,
    token: str | None = None,
) -> IngestResult:
    """Validate, copy, read and record one workbook. The original is never modified.

    Order matters: the copy is read, never the original, and the original is
    re-hashed before the manifest is written. If it changed, OriginalModifiedError
    is raised and no manifest.json exists, so a run folder without one is a failed run.
    """
    source = validate_input(path)
    info = create_run(source, runs_root, now=now, token=token)
    data = read_workbook(info.input_path)  # the COPY, never the original
    original_sha256_after = verify_original_untouched(source, info.original_sha256)

    manifest = RunManifest(
        run_id=info.run_id,
        created_utc=info.created_utc,
        cleanslate_version=__version__,
        python_version=platform.python_version(),
        pandas_version=pd.__version__,
        openpyxl_version=openpyxl.__version__,
        original_filename=info.original_filename,
        original_size_bytes=info.original_size_bytes,
        original_sha256=info.original_sha256,
        copy_sha256=info.copy_sha256,
        original_sha256_after=original_sha256_after,
        sheets=data.sheet_infos,
        warnings=data.warnings,
    )

    manifest_path = info.run_dir / MANIFEST_FILENAME
    manifest_path.write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8", newline="\n"
    )
    return IngestResult(
        manifest=manifest,
        run_dir=info.run_dir,
        manifest_path=manifest_path,
        sheets=data.sheets,
    )
