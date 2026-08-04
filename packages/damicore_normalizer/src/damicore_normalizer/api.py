from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from damicore_normalizer.config import NormalizationConfig
from damicore_normalizer.csv_reader import scan_csv
from damicore_normalizer.errors import NormalizerError
from damicore_normalizer.manifest import (
    NormalizationInput,
    NormalizationManifest,
    NormalizationResult,
)


def _sha256(path: Path, chunk_size: int = 4_194_304) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: object) -> None:
    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def normalize_csv(
    csv_path: str | Path,
    output_dir: str | Path,
    *,
    config: NormalizationConfig | None = None,
) -> NormalizationResult:
    """Normalize a local CSV into deterministic versioned object artifacts."""
    settings = config or NormalizationConfig()
    source = Path(csv_path).resolve()
    if not source.is_file():
        raise NormalizerError(
            f"CSV path is not a regular file: {source}",
            code="input_validation_error",
        )
    before = source.stat()
    destination = Path(output_dir).resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise NormalizerError("output_dir must be absent or empty", code="output_conflict_error")
    destination.mkdir(parents=True, exist_ok=True)
    scan = scan_csv(source, settings, objects_dir=destination / "objects")
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise NormalizerError("CSV changed during normalization", code="input_drift")
    for item in scan.objects:
        object_path = destination / item.relative_path
        if object_path.stat().st_size != item.size_bytes or _sha256(object_path) != item.sha256:
            raise NormalizerError(
                f"normalized object failed validation: {item.object_id}",
                code="artifact_validation_error",
            )
    manifest_path = destination / "manifest.json"
    manifest = NormalizationManifest(
        schema_version=1,
        input=NormalizationInput(
            path=str(source),
            sha256=_sha256(source),
            size_bytes=before.st_size,
            delimiter=settings.delimiter,
            encoding=settings.encoding,
            split=settings.split,
        ),
        objects=scan.objects,
    )
    _atomic_json(manifest_path, manifest.model_dump(mode="json"))
    return NormalizationResult(
        manifest_path=manifest_path,
        object_count=len(scan.objects),
        total_bytes=scan.total_bytes,
        objects=scan.objects,
    )
