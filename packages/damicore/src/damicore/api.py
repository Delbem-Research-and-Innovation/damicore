from __future__ import annotations

import csv
import hashlib
import json
import logging
import shutil
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
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
    json_mapping,
    sha256_file,
)
from damicore.pipeline import (
    PipelineJournal,
    resume_fingerprint,
    runtime_fingerprint,
    utc_now,
)
from damicore.progress import distance_progress
from damicore.result import DamicoreResult, RunReport, artifact_paths

SCHEMA_VERSION = 1
# Read from the installed distribution rather than restated here. This value is stamped
# into every manifest as run provenance, so a third copy of the version string could put
# a number in an artifact that no distribution ever carried. It raises when damicore is
# not installed, which is the honest outcome: there is no correct value to fall back to.
VERSION = metadata.version("damicore")
logger = logging.getLogger(__name__)

# ResourceLimitError itself carries the distinction between CSV size and object count,
# because that is what tells a caller whether the run is reshapable at all: a wider CSV
# stays feasible, more rows does not.
_SCALE_GUIDANCE = (
    "NCD is quadratic and Neighbor Joining cubic in the object count, so a multi-gigabyte CSV "
    "stays feasible while the object count is moderate, which is the usual case for "
    "split='columns'. Streaming and memory maps bound RAM but not that work, so split='rows' "
    "over a large file creates one object per row and is rejected here rather than later. "
    "Reshape the split, reduce the input, or raise individual ResourceLimits after reviewing "
    "estimate(); free disk is never bypassed."
)


def _execution(execution: ExecutionConfig | None) -> ExecutionConfig:
    try:
        return execution or ExecutionConfig()
    except ValidationError as exc:
        raise ConfigurationError(str(exc)) from exc


# The public API takes these as `str` so a caller gets ConfigurationError rather than a
# TypeError, but every stage config declares them as literals. Validating by *returning* the
# literal makes the narrowing part of the contract, so no call site needs a suppression and
# the rejection message has one definition.
def _validated_split(split: str) -> Literal["columns", "rows"]:
    if split == "columns":
        return "columns"
    if split == "rows":
        return "rows"
    raise ConfigurationError("split must be exactly 'columns' or 'rows'")


def _validated_compressor(compressor: str) -> Literal["zlib", "gzip"]:
    if compressor == "zlib":
        return "zlib"
    if compressor == "gzip":
        return "gzip"
    raise ConfigurationError("compressor must be exactly 'zlib' or 'gzip'")


def _normalization_config(
    split: Literal["columns", "rows"],
    delimiter: str,
    encoding: str,
    execution: ExecutionConfig,
) -> NormalizationConfig:
    try:
        return NormalizationConfig(
            split=split,
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
    """Inspect exact resource requirements without creating run artifacts.

    The whole CSV is hashed and scanned, but nothing is written: no run directory, no
    normalized objects. Exceeding a limit is not a failure here, which is what makes this the
    cheap way to decide whether a run is worth starting.

    Parameters
    ----------
    split
        Exactly ``"columns"`` or ``"rows"``. It decides what one object is, and therefore the
        object count that every resource gate is quadratic or cubic in.
    keep_normalized
        Accepted for parity with :func:`run` and deliberately ignored: normalized bytes exist
        on disk while a run is in progress either way, so they are always counted.
    execution
        ``None`` uses the defaults. Free disk is measured against ``./damicore-results``,
        since no output directory has been chosen yet; a run writing elsewhere may see a
        different amount of free space.

    Returns
    -------
    ResourceEstimate
        Returned whether or not the run fits. ``within_limits`` is ``False`` exactly when
        ``violations`` is non-empty, and ``violations`` names each failed gate.

    Raises
    ------
    ConfigurationError
        ``split`` is not one of the two accepted values, or ``delimiter``, ``encoding`` or
        ``execution`` is rejected by validation.
    InputValidationError
        ``csv_path`` is not a readable regular file, or the file changed while it was being
        hashed and scanned (code ``input_drift``).
    CSVFormatError
        The CSV violates the CSV contract.
    """
    checked_split = _validated_split(split)
    settings = _execution(execution)
    _normalization_config(checked_split, delimiter, encoding, settings)
    return preflight(
        csv_path,
        split=checked_split,
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
    # np.load is untyped; bind the result once so the block arithmetic below is checked.
    matrix: npt.NDArray[np.float64] = np.load(path, mmap_mode="r", allow_pickle=False)
    minimum = float("inf")
    maximum = float("-inf")
    out_of_range = 0
    for start in range(0, matrix.shape[0], block_size):
        stop = min(start + block_size, matrix.shape[0])
        block = matrix[start:stop]
        minimum = min(minimum, float(np.min(block)))
        maximum = max(maximum, float(np.max(block)))
        # np.count_nonzero's stub is partially unknown under strict mode; the block is typed.
        outside = np.count_nonzero(  # pyright: ignore[reportUnknownMemberType]
            np.logical_or(block < 0, block > 1)
        )
        out_of_range += int(outside)
    return minimum, maximum, out_of_range


def _peak_rss() -> int | None:
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, OSError):
        return None
    return value if sys.platform == "darwin" else value * 1024


def _stage_seconds(journal: PipelineJournal, stage: str) -> float:
    metrics = json_mapping(json_mapping(journal.receipts.get(stage)).get("metrics"))
    seconds = metrics.get("seconds", 0.0)
    return float(seconds) if isinstance(seconds, (int, float)) else 0.0


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
            "updated_at": utc_now(),
            "failed_stage": stage,
            "stages": journal.receipts,
        }
    )
    atomic_json(journal.manifest_path, journal.manifest)
    logger.error(
        "run_interrupted" if interrupted else "run_failed",
        extra={"stage": stage, "error_type": type(error).__name__},
    )


# How a stage failure becomes a public failure: the stage's own base error selects the row,
# its code selects the class, and an unmapped code falls back to the stage's generic class.
# The four stage bases all accept a `code`, which `type[Exception]` would not express.
StageErrorType = (
    type[NormalizerError] | type[DistanceError] | type[TreeBuilderError] | type[ClusterizerError]
)

_STAGE_TRANSLATIONS: tuple[
    tuple[StageErrorType, dict[str, type[DamicoreError]], type[DamicoreError]], ...
] = (
    (
        NormalizerError,
        {
            "output_conflict_error": OutputDirectoryConflictError,
            "artifact_validation_error": ArtifactValidationError,
            "csv_format_error": CSVFormatError,
            "input_drift": InputValidationError,
        },
        NormalizationError,
    ),
    (
        DistanceError,
        {
            "checkpoint_mismatch_error": CheckpointMismatchError,
            "output_directory_conflict_error": OutputDirectoryConflictError,
            "artifact_validation_error": ArtifactValidationError,
            "compression_error": CompressionError,
            "distance_matrix_validation_error": DistanceMatrixValidationError,
        },
        DistanceComputationError,
    ),
    (
        TreeBuilderError,
        {
            "output_directory_conflict_error": OutputDirectoryConflictError,
            "artifact_validation_error": ArtifactValidationError,
            "tree_format_error": TreeFormatError,
        },
        TreeBuildError,
    ),
    (
        ClusterizerError,
        {
            "output_directory_conflict_error": OutputDirectoryConflictError,
            "tree_format_error": TreeFormatError,
        },
        ClusterizationError,
    ),
)

# A public code is the class name in snake_case, which DamicoreError already derives. A
# stage code must therefore never be forwarded, or the public code would report the stage's
# internal vocabulary instead of the raised class. input_drift is the single sanctioned
# specialization in 0.1.
_PRESERVED_CODES = frozenset({"input_drift"})


def _translated_stage_error(error: Exception, stage: str | None = None) -> DamicoreError:
    code = str(getattr(error, "code", ""))
    for base, by_code, fallback in _STAGE_TRANSLATIONS:
        if isinstance(error, base):
            translated = by_code.get(code, fallback)
            return translated(
                str(error),
                code=code if code in _PRESERVED_CODES else None,
                stage=stage,
            )
    return DamicoreError(str(error), stage=stage)


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
    """Execute, verify, and if possible resume the complete DAMICORE pipeline.

    Preflight, normalization, the exact NCD matrix, Neighbor Joining, and FastGreedy run in
    that order, and the artifacts they leave behind are cross-checked against one another
    before the run is marked ``completed``. Once the run directory exists, a failure or an
    interruption still writes ``report.json`` and updates ``manifest.json`` before the
    exception propagates, so the partial state stays diagnosable and, where the checkpoints
    allow it, resumable.

    The distance stage spawns worker processes, which re-import the calling module, whenever
    ``execution.workers`` resolves above ``1``; ``"auto"`` resolves from the CPU count, so
    only an explicit ``workers=1`` rules the pool out. A call at module level in a ``.py``
    script must therefore sit under ``if __name__ == "__main__":``; a notebook or REPL already
    satisfies this.

    Parameters
    ----------
    split
        Exactly ``"columns"`` or ``"rows"``. It decides what one object is, and therefore the
        object count that the resource gates are quadratic and cubic in.
    compressor
        Exactly ``"zlib"`` or ``"gzip"``. NCD values are compressor-dependent, so changing it
        changes the run identity and the results, not merely their cost.
    num_clusters
        ``None`` lets FastGreedy choose the cut. Otherwise the upper bound is the object count
        this CSV produces with this ``split``, which is only known after preflight, so an
        oversized value is rejected there rather than at call time.
    output_dir
        ``None`` writes to ``./damicore-results/<run_id>``, where ``run_id`` is derived from
        the input hash and the configuration, so repeating a call lands in the same directory
        and reuses or resumes it. An explicit directory is used as given; it may be absent,
        empty, or a compatible earlier run, and is never overwritten.
    keep_normalized
        Keeps ``normalization/`` in the run directory. Otherwise it is deleted once
        verification succeeds, since the objects are reproducible from the CSV.
    progress
        Renders a progress bar for the distance stage through ``tqdm``. Purely presentational.
    execution
        ``None`` uses the defaults: automatic worker count, resume and completed-run reuse
        enabled, and the default ``ResourceLimits``.

    Returns
    -------
    DamicoreResult
        The verified result, loaded through :func:`load_result`. It owns an open memory map
        of ``distance.npy``; call ``close()`` when finished with it.

    Raises
    ------
    ConfigurationError
        An argument or configuration value is invalid, including ``num_clusters`` above the
        object count. Raised before any run directory is created.
    InputValidationError
        ``csv_path`` is not a readable regular file, or its bytes changed between preflight
        and normalization (code ``input_drift``).
    CSVFormatError
        The CSV violates the CSV contract.
    ResourceLimitError
        Preflight projected the run outside ``execution.limits``. ``context["estimate"]``
        holds the ``ResourceEstimate`` behind the decision.
    OutputDirectoryConflictError
        ``output_dir`` is not a directory, holds no readable DAMICORE manifest, belongs to a
        different input or configuration, or holds a compatible run that ``reuse_completed``
        or ``resume`` forbids continuing.
    CheckpointMismatchError
        An incomplete run in ``output_dir`` was produced under a different runtime
        fingerprint, or a checkpoint disagrees with the artifacts beside it.
    CompressionError
        The compressor rejected an object.
    DistanceComputationError
        The NCD stage failed, including a worker pool that died.
    DistanceMatrixValidationError
        The NCD stage's own check found the computed matrix not finite, zero-diagonal, and
        symmetric.
    NormalizationError, TreeBuildError, TreeFormatError, ClusterizationError
        The corresponding stage failed with no more specific cause. ``TreeBuildError`` also
        covers the tree stage rejecting the matrix it was given, which does not surface as
        ``DistanceMatrixValidationError``.
    ArtifactValidationError
        An artifact failed its schema, its recorded hash or size, path containment, or the
        cross-artifact verification.
    DamicoreError
        Any other failure inside the pipeline, named by the underlying exception type.
    KeyboardInterrupt
        Re-raised unchanged, after the run is recorded as interrupted.
    """
    settings = _execution(execution)
    checked_split = _validated_split(split)
    checked_compressor = _validated_compressor(compressor)
    normalization_config = _normalization_config(checked_split, delimiter, encoding, settings)
    try:
        distance_config = DistanceConfig(
            compressor=checked_compressor,
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
        split=checked_split,
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
            f"Resource limits exceeded: {', '.join(preview.violations)}. {_SCALE_GUIDANCE}",
            estimate=preview,
        )
    # The upper bound on num_clusters is part of the argument contract, but it is expressed
    # in leaves, so preflight is the earliest point that can decide it. Checking here keeps a
    # rejected argument from paying for normalization, the NCD matrix and the tree first.
    if num_clusters is not None and num_clusters > preview.object_count:
        raise ConfigurationError(
            f"num_clusters must be between 1 and the {preview.object_count} objects this CSV "
            f"produces with split={checked_split!r}; got {num_clusters}"
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
    # iterdir() on an existing non-directory raises NotADirectoryError, which is neither a
    # public error nor a documented exit code, so the type is checked before it is walked.
    if run_dir.exists() and not run_dir.is_dir():
        raise OutputDirectoryConflictError(f"Output path is not a directory: {run_dir}")
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
        recorded_runtime = {
            key: str(item) for key, item in json_mapping(existing_manifest.get("runtime")).items()
        }
        if not recorded_runtime or resume_fingerprint(recorded_runtime) != resume_fingerprint(
            runtime_fingerprint()
        ):
            raise CheckpointMismatchError(
                "Incomplete run was created by a different runtime fingerprint"
            )
        logger.info("resume_started", extra={"run_id": run_id})
    else:
        run_dir.mkdir(parents=True, exist_ok=True)

    created_at = utc_now()
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
            modularity=clustered.modularity,
            timings_seconds=timings,
            verification=verification,
        )
        atomic_json(run_dir / "report.json", report.model_dump(mode="json"))
        manifest.update(
            {
                "status": "completed",
                "updated_at": utc_now(),
                "completed_at": utc_now(),
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
        # Name the underlying failure: without it a MemoryError and an OSError produce
        # byte-identical report.json files, and the report is all a user has after the fact.
        translated = DamicoreError(
            f"Pipeline failed during {current_stage}: {type(exc).__name__}: {exc}"
        )
        _write_failure(journal, preview, current_stage, translated, interrupted=False)
        raise translated from exc


def load_result(output_dir: str | Path) -> DamicoreResult:
    """Load and verify a completed DAMICORE result without executing artifact code.

    Every artifact the manifest declares is re-checked against its recorded size and SHA-256,
    and any entry that is absolute, escapes the run directory, or is a symlink is rejected
    before it is read. The matrix is memory-mapped with ``allow_pickle=False``, so no artifact
    can execute code on load. Only runs whose manifest and report both say ``completed``, at
    the current schema version, can be loaded; a failed or interrupted run is diagnostic only.

    Returns
    -------
    DamicoreResult
        A fresh result that owns its own open memory map of ``distance.npy``. Every call
        produces an independent one, and each has to be closed by whoever received it.

    Raises
    ------
    ArtifactValidationError
        The only public failure of this function: a missing, unreadable, incomplete, or
        wrong-version manifest or report; a hash or size mismatch; a path that escapes the
        run directory; or a membership, cluster, or Newick artifact that does not parse.
    """
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
