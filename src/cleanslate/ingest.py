"""Stage 1: validate the input file, then copy, read and record it.

This file grows over Stage 1. So far it holds validate_input and read_workbook.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from cleanslate.errors import (
    CorruptWorkbookError,
    EmptyFileError,
    InputError,
    InputNotFoundError,
    UnsupportedFileTypeError,
)
from cleanslate.models import SheetInfo

SUPPORTED_SUFFIX = ".xlsx"


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
