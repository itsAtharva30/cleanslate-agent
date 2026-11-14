"""Stage 1: validate the input file, then copy, read and record it.

This file grows over Stage 1. For now it holds validate_input only.
"""

from pathlib import Path

from openpyxl import load_workbook

from cleanslate.errors import (
    CorruptWorkbookError,
    EmptyFileError,
    InputError,
    InputNotFoundError,
    UnsupportedFileTypeError,
)

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
