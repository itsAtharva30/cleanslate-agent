"""Pydantic models for the run manifest (manifest.json).

The manifest records names, hashes, counts, versions and warnings. It never
holds cell contents: extra fields are forbidden, so none can slip in.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

NonNegInt = Annotated[StrictInt, Field(ge=0)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
SheetState = Literal["visible", "hidden", "veryHidden"]


class _ManifestBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SheetInfo(_ManifestBase):
    name: str
    state: SheetState
    n_rows: NonNegInt
    n_cols: NonNegInt
    merged_ranges: NonNegInt = 0
    formula_cells: NonNegInt = 0


class RunManifest(_ManifestBase):
    schema_version: Literal[1] = 1
    run_id: str
    created_utc: str
    cleanslate_version: str
    python_version: str
    pandas_version: str
    openpyxl_version: str
    original_filename: str
    original_size_bytes: NonNegInt
    original_sha256: Sha256
    copy_sha256: Sha256
    original_sha256_after: Sha256 | None = None
    sheets: list[SheetInfo]
    warnings: list[str] = Field(default_factory=list)
