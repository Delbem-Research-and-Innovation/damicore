from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ObjectDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    object_id: str
    label: str
    relative_path: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("relative_path")
    @classmethod
    def _relative_path_is_contained(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("relative_path must be a contained POSIX path")
        return value


class DelimitedDatasetInput(BaseModel):
    """One delimited-text file split into objects. `.csv`, `.tsv`, and `.txt` are this."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    kind: Literal["delimited"]
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    delimiter: str = Field(min_length=1, max_length=1)
    encoding: str
    split: Literal["columns", "rows"]


class SpreadsheetDatasetInput(BaseModel):
    """One worksheet of an `.xlsx`/`.xlsm` workbook split into objects.

    `sheet` is resolved rather than defaulted: it names the worksheet actually read, so a
    manifest never leaves which sheet was analyzed to be inferred. `cell_text_rule` names
    the rule that turned typed cells into text, because that rule -- not the parsing
    library -- is what the object bytes depend on.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    kind: Literal["xlsx"]
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    sheet: str
    split: Literal["columns", "rows"]
    cell_text_rule: Literal["v1"]


class FileCorpusInput(BaseModel):
    """A set of files that are already the objects.

    `sha256` is a digest over the whole set rather than over one file, because no single
    input file exists to identify the run. `root` is the directory the labels are relative
    to, which is what makes them unique.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    kind: Literal["files"]
    root: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    file_count: int = Field(ge=2)
    recursive: bool
    include_hidden: bool


# Discriminated on `kind`, so an input block is parsed into exactly one variant and a field
# belonging to another variant is rejected rather than ignored. The union is what makes
# `split`, `delimiter`, and `encoding` conditional on the source instead of universal.
NormalizationInput = Annotated[
    DelimitedDatasetInput | SpreadsheetDatasetInput | FileCorpusInput,
    Field(discriminator="kind"),
]

# The encoding that produced the object bytes. An NCD value is only meaningful relative to
# it, so it is recorded rather than assumed. `raw-bytes/1` is the honest name for adopted
# files, whose objects are the user's bytes unchanged.
ObjectEncoding = Literal["json-lines/1", "raw-bytes/1"]


class NormalizationManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[2]
    object_encoding: ObjectEncoding
    input: NormalizationInput
    objects: tuple[ObjectDescriptor, ...]

    @model_validator(mode="after")
    def _encoding_matches_the_source(self) -> Self:
        expected = "raw-bytes/1" if self.input.kind == "files" else "json-lines/1"
        if self.object_encoding != expected:
            raise ValueError(f"{self.input.kind} objects must carry object_encoding {expected}")
        return self


class NormalizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    manifest_path: Path
    object_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    objects: tuple[ObjectDescriptor, ...]
