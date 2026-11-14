import pytest
from pydantic import ValidationError

from cleanslate.models import RunManifest, SheetInfo

HASH_A = "a" * 64


def make_sheet(**overrides):
    data = {"name": "Sales", "state": "visible", "n_rows": 10, "n_cols": 4}
    data.update(overrides)
    return SheetInfo(**data)


def make_manifest(**overrides):
    data = {
        "run_id": "20261113T101530Z_ab12cd",
        "created_utc": "2026-11-13T10:15:30Z",
        "cleanslate_version": "0.0.1",
        "python_version": "3.14.4",
        "pandas_version": "2.3.3",
        "openpyxl_version": "3.1.5",
        "original_filename": "sales.xlsx",
        "original_size_bytes": 2048,
        "original_sha256": HASH_A,
        "copy_sha256": HASH_A,
        "sheets": [make_sheet()],
    }
    data.update(overrides)
    return RunManifest(**data)


def test_defaults_are_applied():
    m = make_manifest()
    assert m.schema_version == 1
    assert m.warnings == []
    assert m.original_sha256_after is None


def test_json_round_trip_is_lossless():
    m = make_manifest(warnings=["hidden sheet: Old"])
    restored = RunManifest.model_validate_json(m.model_dump_json())
    assert restored == m


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        make_manifest(cell_values=[["secret"]])


@pytest.mark.parametrize("bad_hash", ["abc", "A" * 64, "g" * 64])
def test_bad_hashes_are_rejected(bad_hash):
    with pytest.raises(ValidationError):
        make_manifest(original_sha256=bad_hash)


@pytest.mark.parametrize("bad_count", ["5", True])
def test_counts_must_be_real_integers(bad_count):
    with pytest.raises(ValidationError):
        make_sheet(n_rows=bad_count)


def test_negative_counts_are_rejected():
    with pytest.raises(ValidationError):
        make_sheet(n_rows=-1)


def test_unknown_sheet_state_is_rejected():
    with pytest.raises(ValidationError):
        make_sheet(state="secret")


def test_warnings_lists_are_not_shared_between_manifests():
    first = make_manifest()
    second = make_manifest()
    first.warnings.append("x")
    assert second.warnings == []
