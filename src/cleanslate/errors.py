"""Custom exceptions for CleanSlate.

Every error the pipeline raises on purpose inherits from CleanSlateError, so
callers (the CLI, later the UI) can catch one base class and show a clear message.
"""


class CleanSlateError(Exception):
    """Base class for all CleanSlate errors."""


class InputError(CleanSlateError):
    """The input file cannot be used."""


class InputNotFoundError(InputError):
    """The path does not exist or is not a file."""


class UnsupportedFileTypeError(InputError):
    """The file extension is not .xlsx."""


class EmptyFileError(InputError):
    """The file has zero bytes."""


class CorruptWorkbookError(InputError):
    """The file has the right extension but cannot be opened as a workbook."""


class IntegrityError(CleanSlateError):
    """A safety check on the original file or its copy failed."""


class CopyMismatchError(IntegrityError):
    """The copy's hash differs from the original's right after copying."""


class OriginalModifiedError(IntegrityError):
    """The original file's hash changed during the run."""
