"""Per-run workspace: create the run folder and a verified copy of the input.

After create_run, the rest of the pipeline works on the copy and never touches
the original file.
"""

import secrets
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cleanslate.errors import CopyMismatchError
from cleanslate.hashing import sha256_file


@dataclass(frozen=True)
class RunInfo:
    """What create_run produced. Step 1.8 turns this into the manifest."""

    run_id: str
    created_utc: str
    run_dir: Path
    input_path: Path
    original_filename: str
    original_size_bytes: int
    original_sha256: str
    copy_sha256: str


def create_run(
    source: str | Path,
    runs_root: str | Path,
    *,
    now: datetime | None = None,
    token: str | None = None,
) -> RunInfo:
    """Copy source into a new run folder and prove the copy is identical.

    Layout: <runs_root>/<UTC timestamp>_<token>/input/<original filename>
    The source is only read. `now` and `token` exist so tests can be deterministic.
    """
    source = Path(source)
    runs_root = Path(runs_root)

    if now is None:
        now = datetime.now(UTC)
    elif now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    else:
        now = now.astimezone(UTC)
    if token is None:
        token = secrets.token_hex(3)

    # Hash first: a missing or unreadable source fails before any folder is made.
    original_sha256 = sha256_file(source)
    original_size = source.stat().st_size

    run_id = f"{now:%Y%m%dT%H%M%SZ}_{token}"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)  # FileExistsError if it exists: never reuse a run
    input_dir = run_dir / "input"
    input_dir.mkdir()

    input_path = input_dir / source.name
    shutil.copy2(source, input_path)

    copy_sha256 = sha256_file(input_path)
    if copy_sha256 != original_sha256:
        raise CopyMismatchError(
            f"Copy differs from the original (original {original_sha256}, "
            f"copy {copy_sha256}). Run folder kept for inspection: {run_dir}"
        )

    return RunInfo(
        run_id=run_id,
        created_utc=f"{now:%Y-%m-%dT%H:%M:%SZ}",
        run_dir=run_dir,
        input_path=input_path,
        original_filename=source.name,
        original_size_bytes=original_size,
        original_sha256=original_sha256,
        copy_sha256=copy_sha256,
    )
