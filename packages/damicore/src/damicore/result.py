from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

import pandas as pd
from damicore_distance import DistanceMatrixView
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from damicore.errors import ArtifactValidationError, OutputDirectoryConflictError
from damicore.manifest import ArtifactRecord, RunManifest, atomic_json


class ArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_dir: Path
    manifest: Path
    report: Path
    distance_matrix: Path
    labels: Path
    tree_json: Path
    tree_newick: Path
    membership: Path
    clusters: Path
    normalization_dir: Path | None
    diagnostics_dir: Path | None


class RunReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    status: Literal["completed", "failed", "interrupted"]
    failed_stage: str | None = None
    object_count: int = 0
    pair_count: int = 0
    community_count: int | None = None
    cluster_count: int | None = None
    effective_workers: int = 1
    csv_chunk_rows: int = 50_000
    compression_chunk_bytes: int = 4_194_304
    pairs_per_shard: int = 10_000
    matrix_bytes: int = 0
    required_free_disk_bytes: int = 0
    peak_rss_bytes: int | None = None
    ncd_min: float | None = None
    ncd_max: float | None = None
    ncd_out_of_range_count: int = 0
    negative_branch_count: int = 0
    modularity: float | None = None
    timings_seconds: dict[str, float] = Field(default_factory=dict)
    verification: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: dict[str, object] | None = None


@dataclass
class DamicoreResult:
    membership: pd.DataFrame
    clusters: dict[int, list[str]]
    tree_newick: str
    distance_matrix: DistanceMatrixView
    report: RunReport
    artifacts: ArtifactPaths

    def save(self, output_dir: str | Path) -> ArtifactPaths:
        destination = Path(output_dir).resolve()
        if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
            raise OutputDirectoryConflictError("Destination must be absent or empty")
        try:
            manifest = RunManifest.model_validate_json(
                self.artifacts.manifest.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError) as exc:
            raise ArtifactValidationError("Result manifest is invalid") from exc
        if manifest.status != "completed":
            raise ArtifactValidationError("Only completed artifacts can be saved")

        run_root = self.artifacts.run_dir.resolve()
        resolved_records: list[tuple[Path, ArtifactRecord]] = []
        seen_targets: set[Path] = set()
        for record in manifest.artifacts.values():
            # key == record.path is already guaranteed by RunManifest's own validator, which
            # ran at the model_validate_json above; re-checking it here would be a second,
            # weaker source of truth for the same rule.
            relative = _contained_relative_path(record.path)
            source = run_root.joinpath(*relative.parts)
            try:
                resolved_source = source.resolve(strict=True)
            except OSError as exc:
                raise ArtifactValidationError("Artifact source does not exist") from exc
            if (
                source.is_symlink()
                or not resolved_source.is_file()
                or not resolved_source.is_relative_to(run_root)
            ):
                raise ArtifactValidationError("Artifact source escapes the run directory")
            target = destination.joinpath(*relative.parts)
            if target == destination / "manifest.json" or target in seen_targets:
                raise ArtifactValidationError("Artifact inventory contains a duplicate target")
            seen_targets.add(target)
            resolved_records.append((resolved_source, record))

        destination.mkdir(parents=True, exist_ok=True)
        for source, record in resolved_records:
            relative = PurePosixPath(record.path)
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.parent.resolve().is_relative_to(destination):
                raise ArtifactValidationError("Artifact target escapes the destination")
            _copy_verified(source, target, record)
        saved_manifest = manifest.model_copy(update={"run_dir": str(destination)})
        atomic_json(destination / "manifest.json", saved_manifest.model_dump(mode="json"))
        return artifact_paths(destination)

    def close(self) -> None:
        self.distance_matrix.close()


def _contained_relative_path(value: str) -> PurePosixPath:
    relative = PurePosixPath(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ArtifactValidationError("Artifact path must be a contained relative POSIX path")
    return relative


def _copy_verified(source: Path, target: Path, record: ArtifactRecord) -> None:
    descriptor, temporary_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    digest = hashlib.sha256()
    size = 0
    try:
        with source.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output_stream:
            while chunk := input_stream.read(4_194_304):
                digest.update(chunk)
                size += len(chunk)
                output_stream.write(chunk)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        if size != record.size_bytes or digest.hexdigest() != record.sha256:
            raise ArtifactValidationError("Artifact hash or size changed before save")
        os.replace(temporary_name, target)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def artifact_paths(run_dir: Path) -> ArtifactPaths:
    normalization = run_dir / "normalization"
    diagnostics = run_dir / "diagnostics"
    return ArtifactPaths(
        run_dir=run_dir,
        manifest=run_dir / "manifest.json",
        report=run_dir / "report.json",
        distance_matrix=run_dir / "distance.npy",
        labels=run_dir / "labels.json",
        tree_json=run_dir / "tree.json",
        tree_newick=run_dir / "tree.nwk",
        membership=run_dir / "membership.csv",
        clusters=run_dir / "clusters.json",
        normalization_dir=normalization if normalization.exists() else None,
        diagnostics_dir=diagnostics if diagnostics.exists() else None,
    )
