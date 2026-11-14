import pytest

from cleanslate import errors


@pytest.mark.parametrize(
    "exc_class",
    [
        errors.InputError,
        errors.InputNotFoundError,
        errors.UnsupportedFileTypeError,
        errors.EmptyFileError,
        errors.CorruptWorkbookError,
        errors.IntegrityError,
        errors.CopyMismatchError,
        errors.OriginalModifiedError,
    ],
)
def test_every_error_inherits_from_base(exc_class):
    assert issubclass(exc_class, errors.CleanSlateError)


def test_input_errors_share_a_family():
    for exc_class in (
        errors.InputNotFoundError,
        errors.UnsupportedFileTypeError,
        errors.EmptyFileError,
        errors.CorruptWorkbookError,
    ):
        assert issubclass(exc_class, errors.InputError)


def test_integrity_errors_are_not_input_errors():
    assert not issubclass(errors.CopyMismatchError, errors.InputError)
    assert not issubclass(errors.OriginalModifiedError, errors.InputError)


def test_base_class_catches_subclass_and_keeps_message():
    with pytest.raises(errors.CleanSlateError, match="no such file"):
        raise errors.InputNotFoundError("no such file: x.xlsx")
