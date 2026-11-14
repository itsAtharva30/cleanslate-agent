import zipfile

import pytest
from openpyxl import Workbook

from cleanslate.errors import (
    CorruptWorkbookError,
    EmptyFileError,
    InputError,
    InputNotFoundError,
    UnsupportedFileTypeError,
)
from cleanslate.hashing import sha256_file
from cleanslate.ingest import validate_input


def make_xlsx(path):
    wb = Workbook()
    wb.active.append(["a", 1])
    wb.save(path)
    return path


def test_valid_workbook_returns_resolved_path(tmp_path):
    f = make_xlsx(tmp_path / "ok.xlsx")
    assert validate_input(f) == f.resolve()


def test_extension_check_ignores_case(tmp_path):
    f = make_xlsx(tmp_path / "OK.XLSX")
    assert validate_input(f) == f.resolve()


def test_accepts_a_string_path(tmp_path):
    f = make_xlsx(tmp_path / "ok.xlsx")
    assert validate_input(str(f)) == f.resolve()


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(InputNotFoundError):
        validate_input(tmp_path / "nope.xlsx")


def test_directory_is_rejected(tmp_path):
    folder = tmp_path / "folder.xlsx"
    folder.mkdir()
    with pytest.raises(InputNotFoundError):
        validate_input(folder)


@pytest.mark.parametrize("name", ["data.csv", "old.xls", "notes.txt"])
def test_wrong_extension_is_rejected(tmp_path, name):
    f = tmp_path / name
    f.write_bytes(b"x")
    with pytest.raises(UnsupportedFileTypeError):
        validate_input(f)


def test_empty_file_is_rejected(tmp_path):
    f = tmp_path / "empty.xlsx"
    f.write_bytes(b"")
    with pytest.raises(EmptyFileError):
        validate_input(f)


def test_text_file_named_xlsx_is_rejected(tmp_path):
    f = tmp_path / "fake.xlsx"
    f.write_text("this is not a workbook")
    with pytest.raises(CorruptWorkbookError):
        validate_input(f)


def test_zip_that_is_not_a_workbook_is_rejected(tmp_path):
    f = tmp_path / "zip.xlsx"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("hello.txt", "hi")
    with pytest.raises(CorruptWorkbookError):
        validate_input(f)


def test_excel_lock_file_is_rejected_with_a_clear_message(tmp_path):
    f = tmp_path / "~$sales.xlsx"
    f.write_bytes(b"x" * 165)
    with pytest.raises(InputError, match="lock file"):
        validate_input(f)


def test_validation_does_not_modify_the_file(tmp_path):
    f = make_xlsx(tmp_path / "ok.xlsx")
    before = sha256_file(f)
    validate_input(f)
    assert sha256_file(f) == before


def test_file_handle_is_released(tmp_path):
    f = make_xlsx(tmp_path / "ok.xlsx")
    validate_input(f)
    f.unlink()
    assert not f.exists()
