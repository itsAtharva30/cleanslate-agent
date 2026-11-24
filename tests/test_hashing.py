import hashlib
import re

import pytest

from cleanslate.hashing import sha256_file

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


@pytest.mark.parametrize(
    ("content", "expected"),
    [(b"", EMPTY_SHA256), (b"abc", ABC_SHA256)],
)
def test_known_vectors(tmp_path, content, expected):
    f = tmp_path / "f.bin"
    f.write_bytes(content)
    assert sha256_file(f) == expected


@pytest.mark.parametrize("chunk_size", [1, 7, 64, 4096])
def test_chunk_size_does_not_change_the_hash(tmp_path, chunk_size):
    data = bytes(range(256)) * 5 + b"tail"
    f = tmp_path / "f.bin"
    f.write_bytes(data)
    assert sha256_file(f, chunk_size=chunk_size) == hashlib.sha256(data).hexdigest()


def test_result_is_64_lowercase_hex(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"x")
    assert re.fullmatch(r"[0-9a-f]{64}", sha256_file(f))


def test_one_changed_byte_changes_the_hash(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"hello")
    before = sha256_file(f)
    f.write_bytes(b"hellp")
    assert sha256_file(f) != before


@pytest.mark.parametrize("bad", [0, -1])
def test_non_positive_chunk_size_is_rejected(tmp_path, bad):
    f = tmp_path / "f.bin"
    f.write_bytes(b"x")
    with pytest.raises(ValueError):
        sha256_file(f, chunk_size=bad)


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path / "nope.xlsx")
