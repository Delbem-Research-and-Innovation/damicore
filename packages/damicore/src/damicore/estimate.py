from __future__ import annotations

import hashlib
import math
import shutil
from pathlib import Path
from typing import Literal

from damicore_normalizer.config import NormalizationConfig
from damicore_normalizer.csv_reader import scan_csv
from damicore_normalizer.errors import NormalizerError
from pydantic import BaseModel, ConfigDict, Field

from damicore.config import ExecutionConfig
from damicore.errors import CSVFormatError, InputValidationError


class ResourceEstimate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    csv_path: Path
    input_sha256: str
    input_size_bytes: int = Field(ge=0)
    split: Literal["columns", "rows"]
    object_count: int = Field(ge=0)
    pair_count: int = Field(ge=0)
    effective_workers: int = Field(gt=0)
    matrix_bytes: int = Field(ge=0)
    tree_workspace_bytes: int = Field(ge=0)
    normalized_bytes: int = Field(ge=0)
    max_serialized_chunk_bytes: int = Field(ge=0)
    estimated_working_memory_bytes: int = Field(ge=0)
    estimated_final_metadata_bytes: int = Field(ge=0)
    estimated_diagnostic_bytes: int = Field(ge=0)
    estimated_artifact_bytes: int = Field(ge=0)
    required_free_disk_bytes: int = Field(ge=0)
    available_free_disk_bytes: int = Field(ge=0)
    within_limits: bool
    violations: list[str]


def _hash(path: Path, chunk_size: int = 4_194_304) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def preflight(
    csv_path: str | Path,
    *,
    split: Literal["columns", "rows"],
    delimiter: str,
    encoding: str,
    keep_normalized: bool,
    save_diagnostics: bool,
    execution: ExecutionConfig,
    disk_target: Path,
) -> ResourceEstimate:
    del keep_normalized
    path = Path(csv_path).resolve()
    if not path.is_file():
        raise InputValidationError(f"CSV path is not a readable regular file: {path}")
    try:
        before = path.stat()
        input_hash = _hash(path)
        after_hash = path.stat()
    except OSError as exc:
        # is_file() answers existence and type, never readability. A file without read
        # permission, on a dropped mount, or removed after the check above passes it and
        # fails here, and the message above already promised this was checked.
        raise InputValidationError(f"CSV path could not be read: {path}") from exc
    if (before.st_size, before.st_mtime_ns) != (after_hash.st_size, after_hash.st_mtime_ns):
        raise InputValidationError("CSV changed during preflight", code="input_drift")
    try:
        scan = scan_csv(
            path,
            NormalizationConfig(
                split=split,
                delimiter=delimiter,
                encoding=encoding,
                chunk_rows=execution.csv_chunk_rows,
            ),
        )
    except NormalizerError as exc:
        error_type = CSVFormatError if exc.code == "csv_format_error" else InputValidationError
        raise error_type(str(exc), code=exc.code, stage="preflight") from exc
    after_scan = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after_scan.st_size, after_scan.st_mtime_ns):
        raise InputValidationError("CSV changed during preflight", code="input_drift")

    objects = len(scan.objects)
    pairs = objects * (objects - 1) // 2
    matrix_bytes = objects * objects * 8
    checkpoint_bytes = math.ceil(pairs / execution.pairs_per_shard) * 256
    label_bytes = sum(len(item.label.encode("utf-8")) for item in scan.objects)
    metadata_bytes = 1_048_576 + objects * 4_096 + 8 * label_bytes
    diagnostic_bytes = (
        objects * objects * 32 + pairs * 96 + 2 * label_bytes if save_diagnostics else 0
    )
    artifact_bytes = (
        scan.total_bytes + 2 * matrix_bytes + checkpoint_bytes + metadata_bytes + diagnostic_bytes
    )
    required_disk = math.ceil(artifact_bytes * execution.limits.required_free_disk_factor)
    working_memory = max(
        6 * scan.max_serialized_chunk_bytes,
        execution.effective_workers * 2 * execution.compression_chunk_bytes
        + execution.pairs_per_shard * 24,
    )
    existing = disk_target
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    available = shutil.disk_usage(existing).free
    checks = [
        (objects > execution.limits.max_objects, "max_objects"),
        (pairs > execution.limits.max_pairs, "max_pairs"),
        (matrix_bytes > execution.limits.max_matrix_bytes, "max_matrix_bytes"),
        (working_memory > execution.limits.max_working_memory_bytes, "max_working_memory_bytes"),
        (required_disk > available, "free_disk"),
    ]
    violations = [name for failed, name in checks if failed]
    return ResourceEstimate(
        csv_path=path,
        input_sha256=input_hash,
        input_size_bytes=before.st_size,
        split=split,
        object_count=objects,
        pair_count=pairs,
        effective_workers=execution.effective_workers,
        matrix_bytes=matrix_bytes,
        tree_workspace_bytes=matrix_bytes,
        normalized_bytes=scan.total_bytes,
        max_serialized_chunk_bytes=scan.max_serialized_chunk_bytes,
        estimated_working_memory_bytes=working_memory,
        estimated_final_metadata_bytes=metadata_bytes,
        estimated_diagnostic_bytes=diagnostic_bytes,
        estimated_artifact_bytes=artifact_bytes,
        required_free_disk_bytes=required_disk,
        available_free_disk_bytes=available,
        within_limits=not violations,
        violations=violations,
    )
