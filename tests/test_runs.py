import re
import shutil
from datetime import UTC, datetime, timedelta, timezone

import pytest

import cleanslate.runs as runs_module
from cleanslate.errors import CopyMismatchError
from cleanslate.hashing import sha256_file
from cleanslate.runs import create_run

NOW = datetime(2026, 11, 14, 10, 15, 30, tzinfo=UTC)


def make_source(tmp_path, name="sales.xlsx", content=b"PK fake workbook bytes"):
    src_dir = tmp_path / "src"
    src_dir.mkdir(exist_ok=True)
    f = src_dir / name
    f.write_bytes(content)
    return f


def test_run_folder_layout(tmp_path):
    src = make_source(tmp_path)
    info = create_run(src, tmp_path / "runs", now=NOW, token="abc123")
    assert info.run_dir == tmp_path / "runs" / "20261114T101530Z_abc123"
    assert info.input_path == info.run_dir / "input" / "sales.xlsx"
    assert info.input_path.is_file()
    assert info.run_id == info.run_dir.name


def test_generated_run_id_has_the_expected_shape(tmp_path):
    info = create_run(make_source(tmp_path), tmp_path / "runs")
    assert re.fullmatch(r"\d{8}T\d{6}Z_[0-9a-f]{6}", info.run_id)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", info.created_utc)


def test_injected_time_is_used_for_id_and_timestamp(tmp_path):
    src = make_source(tmp_path)
    info = create_run(src, tmp_path / "runs", now=NOW, token="t")
    assert info.run_id == "20261114T101530Z_t"
    assert info.created_utc == "2026-11-14T10:15:30Z"


def test_non_utc_time_is_converted_to_utc(tmp_path):
    ist = timezone(timedelta(hours=5, minutes=30))
    local = datetime(2026, 11, 14, 15, 45, 30, tzinfo=ist)
    src = make_source(tmp_path)
    info = create_run(src, tmp_path / "runs", now=local, token="t")
    assert info.run_id == "20261114T101530Z_t"
    assert info.created_utc == "2026-11-14T10:15:30Z"


def test_naive_time_is_rejected(tmp_path):
    src = make_source(tmp_path)
    with pytest.raises(ValueError, match="timezone-aware"):
        create_run(src, tmp_path / "runs", now=datetime(2026, 11, 14))


def test_copy_is_byte_identical_and_hashes_match(tmp_path):
    src = make_source(tmp_path)
    info = create_run(src, tmp_path / "runs", now=NOW, token="a")
    assert info.input_path.read_bytes() == src.read_bytes()
    assert info.original_sha256 == info.copy_sha256 == sha256_file(src)


def test_metadata_describes_the_original(tmp_path):
    src = make_source(tmp_path, name="Q3 report.xlsx", content=b"12345")
    info = create_run(src, tmp_path / "runs", now=NOW, token="a")
    assert info.original_filename == "Q3 report.xlsx"
    assert info.original_size_bytes == 5


def test_original_is_unchanged(tmp_path):
    src = make_source(tmp_path)
    before = sha256_file(src)
    create_run(src, tmp_path / "runs")
    assert sha256_file(src) == before


def test_missing_runs_root_is_created(tmp_path):
    root = tmp_path / "deep" / "runs"
    info = create_run(make_source(tmp_path), root, now=NOW, token="a")
    assert info.run_dir.parent == root


def test_existing_run_folder_is_never_reused(tmp_path):
    src = make_source(tmp_path)
    root = tmp_path / "runs"
    create_run(src, root, now=NOW, token="same")
    with pytest.raises(FileExistsError):
        create_run(src, root, now=NOW, token="same")


def test_corrupted_copy_raises_copy_mismatch(tmp_path, monkeypatch):
    src = make_source(tmp_path)
    before = sha256_file(src)
    real_copy = shutil.copy2

    def bad_copy(source, destination):
        real_copy(source, destination)
        with open(destination, "ab") as f:
            f.write(b"x")

    monkeypatch.setattr(runs_module.shutil, "copy2", bad_copy)
    with pytest.raises(CopyMismatchError):
        create_run(src, tmp_path / "runs")
    assert sha256_file(src) == before


def test_missing_source_fails_before_creating_any_folder(tmp_path):
    root = tmp_path / "runs"
    with pytest.raises(FileNotFoundError):
        create_run(tmp_path / "nope.xlsx", root)
    assert not root.exists()


def test_two_runs_get_separate_folders(tmp_path):
    src = make_source(tmp_path)
    first = create_run(src, tmp_path / "runs")
    second = create_run(src, tmp_path / "runs")
    assert first.run_dir != second.run_dir
