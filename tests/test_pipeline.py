import json
import platform
from datetime import UTC, datetime

import openpyxl
import pandas as pd
import pytest
from openpyxl import Workbook

import cleanslate.ingest as ingest_module
from cleanslate import __version__
from cleanslate.errors import (
    CorruptWorkbookError,
    EmptyFileError,
    InputNotFoundError,
    OriginalModifiedError,
    UnsupportedFileTypeError,
)
from cleanslate.hashing import sha256_file
from cleanslate.ingest import ingest, verify_original_untouched
from cleanslate.models import RunManifest

NOW = datetime(2026, 11, 15, 9, 30, 0, tzinfo=UTC)


def make_messy(path):
    wb = Workbook()
    main = wb.active
    main.title = "Main"
    main.append(["id", "qty", "total"])
    main.append(["007", 2, "=B2*10"])
    main.merge_cells("A4:B4")
    main["A4"] = "merged"
    hidden = wb.create_sheet("Hid")
    hidden.append([1])
    hidden.sheet_state = "hidden"
    wb.save(path)
    return path


@pytest.fixture
def source(tmp_path):
    folder = tmp_path / "src"
    folder.mkdir()
    return make_messy(folder / "sales.xlsx")


def test_happy_path_creates_run_folder_copy_and_manifest(tmp_path, source):
    root = tmp_path / "runs"
    result = ingest(source, root, now=NOW, token="abc123")
    assert result.run_dir == root / "20261115T093000Z_abc123"
    copy = result.run_dir / "input" / "sales.xlsx"
    assert copy.is_file()
    assert sha256_file(copy) == sha256_file(source)
    assert result.manifest_path == result.run_dir / "manifest.json"
    assert result.manifest_path.is_file()


def test_manifest_on_disk_matches_the_returned_manifest(tmp_path, source):
    result = ingest(source, tmp_path / "runs")
    text = result.manifest_path.read_text(encoding="utf-8")
    assert RunManifest.model_validate_json(text) == result.manifest


def test_manifest_hashes_prove_nothing_changed(tmp_path, source):
    before = sha256_file(source)
    m = ingest(source, tmp_path / "runs").manifest
    assert m.original_sha256 == m.copy_sha256 == m.original_sha256_after == before
    assert m.original_filename == "sales.xlsx"
    assert m.original_size_bytes == source.stat().st_size


def test_manifest_records_versions(tmp_path, source):
    m = ingest(source, tmp_path / "runs").manifest
    assert m.cleanslate_version == __version__
    assert m.python_version == platform.python_version()
    assert m.pandas_version == pd.__version__
    assert m.openpyxl_version == openpyxl.__version__


def test_manifest_lists_sheets_and_hazard_warnings(tmp_path, source):
    m = ingest(source, tmp_path / "runs").manifest
    assert [s.name for s in m.sheets] == ["Main", "Hid"]
    text = "\n".join(m.warnings)
    assert "Hidden sheet: 'Hid'" in text
    assert "Merged cells in 'Main'" in text
    assert "Formulas in 'Main'" in text


def test_manifest_file_never_contains_cell_contents(tmp_path):
    wb = Workbook()
    wb.active.title = "Main"
    wb.active.append(["SECRET-123", "=1+1"])
    f = tmp_path / "s.xlsx"
    wb.save(f)
    result = ingest(f, tmp_path / "runs")
    text = result.manifest_path.read_text(encoding="utf-8")
    assert "SECRET" not in text
    assert json.loads(text)["original_filename"] == "s.xlsx"


def test_original_is_unchanged_after_ingest(tmp_path, source):
    before = sha256_file(source)
    ingest(source, tmp_path / "runs")
    assert sha256_file(source) == before


def test_workbook_is_read_from_the_copy(tmp_path, source, monkeypatch):
    seen = []
    real = ingest_module.read_workbook

    def recording(path):
        seen.append(path)
        return real(path)

    monkeypatch.setattr(ingest_module, "read_workbook", recording)
    result = ingest(source, tmp_path / "runs")
    assert len(seen) == 1
    assert seen[0] == result.run_dir / "input" / "sales.xlsx"
    assert seen[0] != source


def test_result_carries_the_raw_frames(tmp_path, source):
    result = ingest(source, tmp_path / "runs")
    assert list(result.sheets) == ["Main", "Hid"]
    assert isinstance(result.sheets["Main"], pd.DataFrame)
    assert result.sheets["Main"].iloc[1, 0] == "007"


@pytest.mark.parametrize(
    ("name", "content", "error"),
    [
        ("missing.xlsx", None, InputNotFoundError),
        ("data.csv", b"a,b", UnsupportedFileTypeError),
        ("empty.xlsx", b"", EmptyFileError),
        ("fake.xlsx", b"not a workbook", CorruptWorkbookError),
    ],
)
def test_bad_input_creates_no_run_folder(tmp_path, name, content, error):
    f = tmp_path / name
    if content is not None:
        f.write_bytes(content)
    root = tmp_path / "runs"
    with pytest.raises(error):
        ingest(f, root)
    assert not root.exists()


def test_verify_returns_the_hash_when_unchanged(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"data")
    expected = sha256_file(f)
    assert verify_original_untouched(f, expected) == expected


def test_verify_raises_when_the_file_changed(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"data")
    expected = sha256_file(f)
    f.write_bytes(b"datb")
    with pytest.raises(OriginalModifiedError):
        verify_original_untouched(f, expected)


def test_tampering_mid_run_is_caught(tmp_path, source, monkeypatch):
    before = sha256_file(source)
    real = ingest_module.read_workbook

    def tampering(path):
        data = real(path)
        with open(source, "ab") as f:  # simulates a sync tool or an autosave
            f.write(b"x")
        return data

    monkeypatch.setattr(ingest_module, "read_workbook", tampering)
    root = tmp_path / "runs"
    with pytest.raises(OriginalModifiedError):
        ingest(source, root)

    run_dirs = list(root.iterdir())
    assert len(run_dirs) == 1  # the run folder is kept for inspection
    assert not (run_dirs[0] / "manifest.json").exists()  # a failed run has no manifest
    copy = run_dirs[0] / "input" / "sales.xlsx"
    assert sha256_file(copy) == before  # the copy still holds the pre-tamper bytes
