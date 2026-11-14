"""File hashing helpers."""

import hashlib
from pathlib import Path

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def sha256_file(path: str | Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Return the SHA-256 of a file as 64 lowercase hex characters.

    The file is read in chunks, so large workbooks never have to fit in memory.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
