from __future__ import annotations

import csv
import hashlib
import json
import logging
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from damicore_clusterizer import (
    ClusterConfig,
    ClusterizerError,
    ClusterResult,
    cluster_tree,
)
from damicore_distance import (
    DistanceConfig,
    DistanceError,
    DistanceMatrixView,
    DistanceResult,
    compute_distance_matrix,
)
from damicore_normalizer import (
    NormalizationConfig,
    NormalizationResult,
    NormalizerError,
    ObjectDescriptor,
    normalize_csv,
)
from damicore_normalizer.manifest import NormalizationManifest
from damicore_tree_builder import (
    Tree,
    TreeBuildConfig,
    TreeBuilderError,
    TreeBuildResult,
    build_tree,
)
from pydantic import ValidationError

from damicore.config import ExecutionConfig
from damicore.errors import (
    ArtifactValidationError,
    CheckpointMismatchError,
    ClusterizationError,
    CompressionError,
    ConfigurationError,
    CSVFormatError,
    DamicoreError,
    DistanceComputationError,
    DistanceMatrixValidationError,
    InputValidationError,
    MaterializationError,
    NormalizationError,
    OutputDirectoryConflictError,
    ResourceLimitError,
    TreeBuildError,
    TreeFormatError,
)
from damicore.estimate import ResourceEstimate, preflight
from damicore.manifest import (
    ClustersArtifact,
    LabelsArtifact,
    RunManifest,
    artifact_record,
    atomic_json,
    sha256_file,
)
from damicore.pipeline import PipelineJournal, resume_fingerprint, runtime_fingerprint
from damicore.progress import distance_progress
from damicore.result import DamicoreResult, RunReport, artifact_paths

SCHEMA_VERSION = 1
VERSION = "0.1.0"
logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _execution(execution: ExecutionConfig | None) -> ExecutionConfig:
    try:
        return execution or ExecutionConfig()
    except ValidationError as exc:
        raise ConfigurationError(str(exc)) from exc


def _normalization_config(
    split: str,
    delimiter: str,
    encoding: str,
    execution: ExecutionConfig,
) -> NormalizationConfig:
    try:
        return NormalizationConfig(
            split=split,  # type: ignore[arg-type] -- public API validates the string
            delimiter=delimiter,
            encoding=encoding,
            chunk_rows=execution.csv_chunk_rows,
        )
    except (LookupError, ValidationError) as exc:
        raise ConfigurationError(str(exc)) from exc


def estimate(
    csv_path: str | Path,
    *,
    split: str = "columns",
    delimiter: str = ",",
    encoding: str = "utf-8",
    keep_normalized: bool = False,
    save_diagnostics: bool = False,
    execution: ExecutionConfig | None = None,
) -> ResourceEstimate:
    """Inspect exact resource requirements without creating run artifacts."""
    if split not in ("columns", "rows"):
        raise ConfigurationError("split must be exactly 'columns' or 'rows'")
    settings = _execution(execution)
    _normalization_config(split, delimiter, encoding, settings)
    return preflight(
        csv_path,
        split=split,  # type: ignore[arg-type] -- validated above
        delimiter=delimiter,
        encoding=encoding,
        keep_normalized=keep_normalized,
        save_diagnostics=save_diagnostics,
        execution=settings,
        disk_target=Path.cwd() / "damicore-results",
    )


def _config_payload(
    *,
    split: str,
    delimiter: str,
    encoding: str,
    compressor: str,
    compression_level: int,
    num_clusters: int | None,
    keep_normalized: bool,
    save_diagnostics: bool,
    execution: ExecutionConfig,
) -> dict[str, object]:
    return {
        "split": split,
        "delimiter": delimiter,
        "encoding": encoding,
        "compressor": compressor,
        "compression_level": compression_level,
        "num_clusters": num_clusters,
        "keep_normalized": keep_normalized,
        "save_diagnostics": save_diagnostics,
        "workers": execution.effective_workers,
        "csv_chunk_rows": execution.csv_chunk_rows,
        "compression_chunk_bytes": execution.compression_chunk_bytes,
        "pairs_per_shard": execution.pairs_per_shard,
        "pandas_materialization_limit_bytes": execution.pandas_materialization_limit_bytes,
        "limits": execution.limits.model_dump(mode="json"),
    }


def _identity(input_hash: str, config: dict[str, object]) -> tuple[str, str]:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    config_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    run_hash = hashlib.sha256(f"{input_hash}{config_hash}{SCHEMA_VERSION}".encode()).hexdigest()
    return config_hash, run_hash[:16]


def _load_normalization(path: Path) -> NormalizationResult:
    try:
        manifest = NormalizationManifest.model_validate_json(path.read_text(encoding="utf-8"))
        objects = tuple(ObjectDescriptor.model_validate(item) for item in manifest.objects)
    except (OSError, ValidationError) as exc:
        raise ArtifactValidationError("Normalization receipt is invalid") from exc
    return NormalizationResult(
        manifest_path=path,
        object_count=len(objects),
        total_bytes=sum(item.size_bytes for item in objects),
        objects=objects,
    )


def _verify_cross_artifacts(
    run_dir: Path,
    normalization: NormalizationResult,
    requested_communities: int | None,
    actual_communities: int,
) -> dict[str, bool]:
    try:
        labels = LabelsArtifact.model_validate_json(
            (run_dir / "labels.json").read_text(encoding="utf-8")
        )
        tree = Tree.model_validate_json((run_dir / "tree.json").read_text(encoding="utf-8"))
        clusters = ClustersArtifact.model_validate_json(
            (run_dir / "clusters.json").read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as exc:
        raise ArtifactValidationError("Final artifact schema validation failed") from exc
    expected_ids = [item.object_id for item in normalization.objects]
    expected_labels = [item.label for item in normalization.objects]
    object_ids = list(labels.object_ids)
    label_values = list(labels.labels)
    matrix = np.load(run_dir / "distance.npy", mmap_mode="r", allow_pickle=False)
    leaf_ids = [node.id for node in tree.nodes if node.kind == "leaf"]
    with (run_dir / "membership.csv").open(encoding="utf-8", newline="") as stream:
        membership = list(csv.DictReader(stream))
    membership_ids = [row["object_id"] for row in membership]
    membership_labels = [row["label"] for row in membership]
    membership_assignment = {row["object_id"]: int(row["cluster"]) for row in membership}
    cluster_items = clusters.clusters
    clustered_ids = [object_id for cluster in cluster_items for object_id in cluster.object_ids]
    cluster_numbers = [cluster.cluster for cluster in cluster_items]
    clusters_assignment = {
        object_id: cluster.cluster for cluster in cluster_items for object_id in cluster.object_ids
    }
    checks = {
        "normalization_to_labels": object_ids == expected_ids and label_values == expected_labels,
        "matrix_shape": matrix.shape == (len(object_ids), len(object_ids)),
        "tree_leaves": set(leaf_ids) == set(object_ids) and len(leaf_ids) == len(object_ids),
        "membership": membership_ids == object_ids
        and membership_labels == label_values
        and len(set(membership_ids)) == len(object_ids),
        "clusters": set(clustered_ids) == set(object_ids) and len(clustered_ids) == len(object_ids),
        "membership_clusters": membership_assignment == clusters_assignment
        and set(membership_assignment.values()) == set(cluster_numbers),
        "cluster_ids": cluster_numbers == list(range(len(cluster_numbers))),
        "requested_communities": requested_communities is None
        or requested_communities == actual_communities,
    }
    if not all(checks.values()):
        raise ArtifactValidationError("Cross-artifact verification failed", checks=checks)
    return checks


def _matrix_statistics(path: Path, block_size: int = 512) -> tuple[float, float, int]:
    matrix = np.load(path, mmap_mode="r", allow_pickle=False)
    minimum = float("inf")
    maximum = float("-inf")
    out_of_range = 0
    for start in range(0, matrix.shape[0], block_size):
        stop = min(start + block_size, matrix.shape[0])
        block = matrix[start:stop]
        minimum = min(minimum, float(np.min(block)))
        maximum = max(maximum, float(np.max(block)))
        out_of_range += int(np.count_nonzero(np.logical_or(block < 0, block > 1)))
    return minimum, maximum, out_of_range


def _peak_rss() -> int | None:
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, OSError):
        return None
    return value if sys.platform == "darwin" else value * 1024


def _stage_seconds(journal: PipelineJournal, stage: str) -> float:
    receipt = journal.receipts.get(stage, {})
    metrics = receipt.get("metrics", {}) if isinstance(receipt, dict) else {}
    return float(metrics.get("seconds", 0.0)) if isinstance(metrics, dict) else 0.0


def _write_failure(
    journal: PipelineJournal,
    preview: ResourceEstimate,
    stage: str,
    error: BaseException,
    *,
    interrupted: bool,
) -> None:
    status = "interrupted" if interrupted else "failed"
    code = getattr(error, "code", type(error).__name__)
    error_detail: dict[str, object] = {
        "error_type": type(error).__name__,
        "code": str(code),
        "error_message": str(error),
    }
    report = RunReport(
        status=status,
        failed_stage=stage,
        object_count=preview.object_count,
        pair_count=preview.pair_count,
        effective_workers=preview.effective_workers,
        matrix_bytes=preview.matrix_bytes,
        required_free_disk_bytes=preview.required_free_disk_bytes,
        peak_rss_bytes=_peak_rss(),
        timings_seconds={
            name: _stage_seconds(journal, name)
            for name in ("normalizing", "distancing", "tree_building", "clusterizing")
        },
        error=error_detail,
    )
    atomic_json(journal.run_dir / "report.json", report.model_dump(mode="json"))
    journal.manifest.update(
        {
            "status": status,
            "updated_at": _utc_now(),
            "failed_stage": stage,
            "stages": journal.receipts,
        }
    )
    atomic_json(journal.manifest_path, journal.manifest)
    logger.error(
        "run_interrupted" if interrupted else "run_failed",
        extra={"stage": stage, "error_type": type(error).__name__},
    )


def _translated_stage_error(error: Exception, stage: str | None = None) -> DamicoreError:
    code = getattr(error, "code", "")
    if isinstance(error, NormalizerError):
        if code == "output_conflict_error":
            return OutputDirectoryConflictError(str(error), code=code)
        if code == "artifact_validation_error":
            return ArtifactValidationError(str(error), code=code)
        if code == "csv_format_error":
            return CSVFormatError(str(error), code=code, stage=stage)
        if code == "input_drift":
            return InputValidationError(str(error), code=code, stage=stage)
        return NormalizationError(str(error), code=code)
    if isinstance(error, DistanceError):
        if code == "checkpoint_mismatch_error":
            return CheckpointMismatchError(str(error), code=code)
        if code == "output_directory_conflict_error":
            return OutputDirectoryConflictError(str(error), code=code)
        if code == "artifact_validation_error":
            return ArtifactValidationError(str(error), code=code)
        if code == "compression_error":
            return CompressionError(str(error), code=code)
        if code == "distance_matrix_validation_error":
            return DistanceMatrixValidationError(str(error), code=code)
        return DistanceComputationError(str(error), code=code)
    if isinstance(error, TreeBuilderError):
        if code == "output_directory_conflict_error":
            return OutputDirectoryConflictError(str(error), code=code)
        if code == "artifact_validation_error":
            return ArtifactValidationError(str(error), code=code)
        if code == "tree_format_error":
            return TreeFormatError(str(error), code=code)
        return TreeBuildError(str(error), code=code)
    if isinstance(error, ClusterizerError):
        if code == "output_directory_conflict_error":
            return OutputDirectoryConflictError(str(error), code=code)
        if code == "tree_format_error":
            return TreeFormatError(str(error), code=code)
        return ClusterizationError(str(error), code=code)
    return DamicoreError(str(error))


def _artifact_inventory(run_dir: Path) -> dict[str, dict[str, object]]:
    paths = [
        run_dir / "report.json",
        run_dir / "distance.npy",
        run_dir / "labels.json",
        run_dir / "tree.json",
        run_dir / "tree.nwk",
        run_dir / "membership.csv",
        run_dir / "clusters.json",
    ]
    for directory_name in ("checkpoints", "diagnostics", "normalization"):
        directory = run_dir / directory_name
        if directory.is_dir():
            paths.extend(path for path in directory.rglob("*") if path.is_file())
    return {
        path.relative_to(run_dir).as_posix(): artifact_record(path, run_dir)
        for path in sorted(paths)
    }


def run(
    csv_path: str | Path,
    *,
    split: str = "columns",
    delimiter: str = ",",
    encoding: str = "utf-8",
    compressor: str = "zlib",
    compression_level: int = 6,
    num_clusters: int | None = None,
    output_dir: str | Path | None = None,
    keep_normalized: bool = False,
    save_diagnostics: bool = False,
    progress: bool = True,
    execution: ExecutionConfig | None = None,
) -> DamicoreResult:
    """Execute, verify, and if possible resume the complete DAMICORE pipeline."""
    settings = _execution(execution)
    if split not in ("columns", "rows"):
        raise ConfigurationError("split must be exactly 'columns' or 'rows'")
    if compressor not in ("zlib", "gzip"):
        raise ConfigurationError("compressor must be exactly 'zlib' or 'gzip'")
    normalization_config = _normalization_config(split, delimiter, encoding, settings)
    try:
        distance_config = DistanceConfig(
            compressor=compressor,  # type: ignore[arg-type] -- validated above
            compression_level=compression_level,
            compression_chunk_bytes=settings.compression_chunk_bytes,
            workers=settings.effective_workers,
            pairs_per_shard=settings.pairs_per_shard,
            resume=settings.resume,
            save_diagnostics=save_diagnostics,
        )
        cluster_config = ClusterConfig(num_clusters=num_clusters)
        tree_config = TreeBuildConfig()
    except ValidationError as exc:
        raise ConfigurationError(str(exc)) from exc

    target_hint = (
        Path(output_dir).resolve() if output_dir is not None else Path.cwd() / "damicore-results"
    )
    preview = preflight(
        csv_path,
        split=split,  # type: ignore[arg-type] -- validated above
        delimiter=delimiter,
        encoding=encoding,
        keep_normalized=keep_normalized,
        save_diagnostics=save_diagnostics,
        execution=settings,
        disk_target=target_hint,
    )
    logger.info(
        "preflight_completed",
        extra={"object_count": preview.object_count, "pair_count": preview.pair_count},
    )
    if not preview.within_limits:
        raise ResourceLimitError(
            "Resource limits exceeded: " + ", ".join(preview.violations),
            estimate=preview,
        )
    config = _config_payload(
        split=split,
        delimiter=delimiter,
        encoding=encoding,
        compressor=compressor,
        compression_level=compression_level,
        num_clusters=num_clusters,
        keep_normalized=keep_normalized,
        save_diagnostics=save_diagnostics,
        execution=settings,
    )
    config_hash, run_id = _identity(preview.input_sha256, config)
    run_dir = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (Path.cwd() / "damicore-results" / run_id).resolve()
    )
    manifest_path = run_dir / "manifest.json"
    existing_manifest: dict[str, Any] | None = None
    if run_dir.exists() and any(run_dir.iterdir()):
        try:
            existing_manifest = RunManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            ).model_dump(mode="json")
        except (OSError, ValidationError) as exc:
            raise OutputDirectoryConflictError(
                "Output directory has no readable DAMICORE manifest"
            ) from exc
        compatible = (
            existing_manifest.get("input", {}).get("sha256") == preview.input_sha256
            and existing_manifest.get("config_hash") == config_hash
            and existing_manifest.get("schema_version") == SCHEMA_VERSION
        )
        if not compatible:
            raise OutputDirectoryConflictError("Output directory belongs to another run")
        if existing_manifest.get("status") == "completed":
            if settings.reuse_completed:
                return load_result(run_dir)
            raise OutputDirectoryConflictError("Completed output reuse is disabled")
        if not settings.resume:
            raise OutputDirectoryConflictError("Incomplete output resume is disabled")
        recorded_runtime = existing_manifest.get("runtime")
        if not isinstance(recorded_runtime, dict) or resume_fingerprint(
            recorded_runtime
        ) != resume_fingerprint(runtime_fingerprint()):
            raise CheckpointMismatchError(
                "Incomplete run was created by a different runtime fingerprint"
            )
        logger.info("resume_started", extra={"run_id": run_id})
    else:
        run_dir.mkdir(parents=True, exist_ok=True)

    created_at = _utc_now()
    manifest = existing_manifest or {
        "schema_version": SCHEMA_VERSION,
        "damicore_version": VERSION,
        "run_id": run_id,
        "status": "created",
        "created_at": created_at,
        "updated_at": created_at,
        "completed_at": None,
        "run_dir": str(run_dir),
        "input": {
            "path": str(preview.csv_path),
            "size_bytes": preview.input_size_bytes,
            "mtime_ns": preview.csv_path.stat().st_mtime_ns,
            "sha256": preview.input_sha256,
        },
        "config": config,
        "config_hash": config_hash,
        "estimate": preview.model_dump(mode="json"),
        "runtime": runtime_fingerprint(),
        "stages": {},
        "artifacts": {},
        "warnings": [],
    }
    atomic_json(manifest_path, manifest)
    journal = PipelineJournal(run_dir, manifest)
    logger.info("run_started", extra={"run_id": run_id})
    journal.transition("preflighted")
    current_stage = "normalizing"
    try:
        normalization_dir = run_dir / "normalization"
        if journal.reusable("normalizing"):
            normalization = _load_normalization(normalization_dir / "manifest.json")
        else:
            if normalization_dir.exists():
                shutil.rmtree(normalization_dir)
            started = journal.stage_started("normalizing", [preview.csv_path])
            normalization = normalize_csv(
                preview.csv_path,
                normalization_dir,
                config=normalization_config,
            )
            normalization_manifest = NormalizationManifest.model_validate_json(
                normalization.manifest_path.read_text(encoding="utf-8")
            )
            if (
                normalization.total_bytes != preview.normalized_bytes
                or normalization_manifest.input.sha256 != preview.input_sha256
                or normalization_manifest.input.size_bytes != preview.input_size_bytes
            ):
                raise InputValidationError(
                    "Preflight and normalization byte counts differ",
                    code="input_drift",
                )
            outputs = [normalization.manifest_path]
            outputs.extend(normalization_dir / item.relative_path for item in normalization.objects)
            journal.stage_completed(
                "normalizing",
                started,
                outputs,
                {
                    "object_count": normalization.object_count,
                    "normalized_bytes": normalization.total_bytes,
                },
            )

        current_stage = "distancing"
        if journal.reusable("distancing"):
            distance = DistanceResult(
                matrix_path=run_dir / "distance.npy",
                labels_path=run_dir / "labels.json",
                object_count=preview.object_count,
                pair_count=preview.pair_count,
                timing=_stage_seconds(journal, "distancing"),
            )
        else:
            for stale in (run_dir / "tree.json", run_dir / "tree.nwk", run_dir / "tree-work.npy"):
                if stale.exists():
                    stale.unlink()
            started = journal.stage_started(
                "distancing",
                [normalization.manifest_path],
            )
            callback, close_progress = distance_progress(progress)
            try:
                distance = compute_distance_matrix(
                    normalization.manifest_path,
                    run_dir,
                    config=distance_config,
                    progress=callback,
                )
            finally:
                close_progress()
            distance_outputs = [
                distance.matrix_path,
                distance.labels_path,
                run_dir / "checkpoints" / "compressed-sizes.json",
                run_dir / "checkpoints" / "distance-shards.json",
            ]
            diagnostics_dir = run_dir / "diagnostics"
            if diagnostics_dir.is_dir():
                distance_outputs.extend(
                    path for path in diagnostics_dir.iterdir() if path.is_file()
                )
            journal.stage_completed(
                "distancing",
                started,
                distance_outputs,
                {"object_count": distance.object_count, "pair_count": distance.pair_count},
            )

        current_stage = "tree_building"
        if journal.reusable("tree_building"):
            tree = TreeBuildResult(
                tree_path=run_dir / "tree.json",
                newick_path=run_dir / "tree.nwk",
                leaf_count=preview.object_count,
                negative_branch_count=int(
                    journal.receipts["tree_building"]["metrics"]["negative_branch_count"]
                ),
                timing=_stage_seconds(journal, "tree_building"),
            )
        else:
            started = journal.stage_started(
                "tree_building",
                [distance.matrix_path, distance.labels_path],
            )
            tree = build_tree(
                distance.matrix_path,
                distance.labels_path,
                run_dir,
                config=tree_config,
            )
            journal.stage_completed(
                "tree_building",
                started,
                [tree.tree_path, tree.newick_path],
                {
                    "leaf_count": tree.leaf_count,
                    "negative_branch_count": tree.negative_branch_count,
                },
            )

        current_stage = "clusterizing"
        if journal.reusable("clusterizing"):
            metrics = journal.receipts["clusterizing"]["metrics"]
            clustered = ClusterResult(
                membership_path=run_dir / "membership.csv",
                clusters_path=run_dir / "clusters.json",
                community_count=int(metrics["community_count"]),
                cluster_count=int(metrics["cluster_count"]),
                modularity=float(metrics["modularity"]),
                branch_length_shift=float(metrics["branch_length_shift"]),
                timing=_stage_seconds(journal, "clusterizing"),
            )
        else:
            for stale in (run_dir / "membership.csv", run_dir / "clusters.json"):
                if stale.exists():
                    stale.unlink()
            started = journal.stage_started("clusterizing", [tree.tree_path])
            clustered = cluster_tree(tree.tree_path, run_dir, config=cluster_config)
            journal.stage_completed(
                "clusterizing",
                started,
                [clustered.membership_path, clustered.clusters_path],
                {
                    "community_count": clustered.community_count,
                    "cluster_count": clustered.cluster_count,
                    "modularity": clustered.modularity,
                    "branch_length_shift": clustered.branch_length_shift,
                },
            )

        current_stage = "verifying"
        journal.transition("verifying")
        verification = _verify_cross_artifacts(
            run_dir,
            normalization,
            num_clusters,
            clustered.community_count,
        )
        ncd_min, ncd_max, out_of_range = _matrix_statistics(distance.matrix_path)
        if not keep_normalized:
            shutil.rmtree(normalization_dir)

        timings = {
            stage: _stage_seconds(journal, stage)
            for stage in ("normalizing", "distancing", "tree_building", "clusterizing")
        }
        timings["total"] = sum(timings.values())
        report = RunReport(
            status="completed",
            object_count=preview.object_count,
            pair_count=preview.pair_count,
            community_count=clustered.community_count,
            cluster_count=clustered.cluster_count,
            effective_workers=settings.effective_workers,
            csv_chunk_rows=settings.csv_chunk_rows,
            compression_chunk_bytes=settings.compression_chunk_bytes,
            pairs_per_shard=settings.pairs_per_shard,
            matrix_bytes=preview.matrix_bytes,
            required_free_disk_bytes=preview.required_free_disk_bytes,
            peak_rss_bytes=_peak_rss(),
            ncd_min=ncd_min,
            ncd_max=ncd_max,
            ncd_out_of_range_count=out_of_range,
            negative_branch_count=tree.negative_branch_count,
            branch_length_shift=clustered.branch_length_shift,
            modularity=clustered.modularity,
            timings_seconds=timings,
            verification=verification,
        )
        atomic_json(run_dir / "report.json", report.model_dump(mode="json"))
        manifest.update(
            {
                "status": "completed",
                "updated_at": _utc_now(),
                "completed_at": _utc_now(),
                "objects": [
                    item.model_dump(mode="json", exclude={"relative_path"})
                    for item in normalization.objects
                ],
                "stages": journal.receipts,
                "cleanup_completed": not keep_normalized,
                "artifacts": _artifact_inventory(run_dir),
            }
        )
        atomic_json(manifest_path, manifest)
        logger.info("verification_completed", extra={"run_id": run_id})
        logger.info("run_completed", extra={"run_id": run_id})
        return load_result(run_dir)
    except KeyboardInterrupt as exc:
        _write_failure(
            journal,
            preview,
            current_stage,
            exc,
            interrupted=True,
        )
        raise
    except DamicoreError as exc:
        logger.error("run_failed", extra={"run_id": run_id, "stage": current_stage})
        _write_failure(journal, preview, current_stage, exc, interrupted=False)
        raise
    except (NormalizerError, DistanceError, TreeBuilderError, ClusterizerError) as exc:
        translated = _translated_stage_error(exc, current_stage)
        _write_failure(journal, preview, current_stage, translated, interrupted=False)
        logger.error("stage_failed", extra={"run_id": run_id, "stage": current_stage})
        raise translated from exc
    except Exception as exc:
        translated = DamicoreError(f"Pipeline failed during {current_stage}")
        _write_failure(journal, preview, current_stage, translated, interrupted=False)
        raise translated from exc


def load_result(output_dir: str | Path) -> DamicoreResult:
    """Load and verify a completed DAMICORE result without executing artifact code."""
    run_dir = Path(output_dir).resolve()
    paths = artifact_paths(run_dir)
    try:
        manifest = RunManifest.model_validate_json(paths.manifest.read_text(encoding="utf-8"))
        if manifest.status != "completed" or manifest.schema_version != SCHEMA_VERSION:
            raise ArtifactValidationError("Only completed schema-v1 runs can be loaded")
        for record in manifest.artifacts.values():
            relative = Path(record.path)
            candidate = (run_dir / relative).resolve()
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not candidate.is_relative_to(run_dir)
                or candidate.is_symlink()
            ):
                raise ArtifactValidationError("Artifact path escapes the run directory")
            if (
                candidate.stat().st_size != record.size_bytes
                or sha256_file(candidate) != record.sha256
            ):
                raise ArtifactValidationError("Artifact hash or size mismatch")
        report = RunReport.model_validate_json(paths.report.read_text(encoding="utf-8"))
        if report.status != "completed":
            raise ArtifactValidationError("Result report is not completed")
        labels_payload = LabelsArtifact.model_validate_json(
            paths.labels.read_text(encoding="utf-8")
        )
        membership = pd.read_csv(
            paths.membership,
            dtype={"object_id": "string", "label": "string", "cluster": "int64"},
            keep_default_na=False,
            na_filter=False,
        )
        if list(membership.columns) != ["object_id", "label", "cluster"]:
            raise ArtifactValidationError("membership.csv columns are invalid")
        cluster_payload = ClustersArtifact.model_validate_json(
            paths.clusters.read_text(encoding="utf-8")
        )
        clusters = {item.cluster: list(item.labels) for item in cluster_payload.clusters}
        tree_newick = paths.tree_newick.read_text(encoding="utf-8").strip()
        if not tree_newick.endswith(";"):
            raise ArtifactValidationError("Newick artifact does not end with semicolon")
    except DamicoreError:
        raise
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
        raise ArtifactValidationError("Could not load completed result") from exc
    view = DistanceMatrixView(
        paths.distance_matrix,
        list(labels_payload.labels),
        materialization_limit_bytes=manifest.config.pandas_materialization_limit_bytes,
        materialization_error=MaterializationError,
    )
    return DamicoreResult(
        membership=membership,
        clusters=clusters,
        tree_newick=tree_newick,
        distance_matrix=view,
        report=report,
        artifacts=paths,
    )
