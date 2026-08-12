from __future__ import annotations

import logging
import platform
import time
import zlib
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from damicore.errors import ArtifactValidationError, CheckpointMismatchError
from damicore.manifest import (
    PipelineCheckpoint,
    artifact_record,
    atomic_json,
    json_mapping,
    json_sequence,
    sha256_file,
)

logger = logging.getLogger(__name__)


# Fields whose equality is required to resume an incomplete run.
# Deliberately narrower than the full runtime record: environment facts such as the
# platform string or sibling-package builds must not spuriously block a valid resume.
RESUME_FINGERPRINT_KEYS = (
    "damicore",
    "python",
    "numpy",
    "igraph",
    "zlib_build",
    "zlib_runtime",
)


def runtime_fingerprint() -> dict[str, str]:
    packages = (
        "damicore",
        "damicore-normalizer",
        "damicore-distance",
        "damicore-tree-builder",
        "damicore-clusterizer",
    )
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "unknown"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": version("numpy"),
        "pandas": version("pandas"),
        "pydantic": version("pydantic"),
        "igraph": version("igraph"),
        "tqdm": version("tqdm"),
        "zlib_build": zlib.ZLIB_VERSION,
        "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION,
        **versions,
    }


def resume_fingerprint(fingerprint: dict[str, str]) -> dict[str, str]:
    """Project the resume-compatibility subset from a full runtime record."""
    return {key: fingerprint[key] for key in RESUME_FINGERPRINT_KEYS if key in fingerprint}


class PipelineJournal:
    def __init__(self, run_dir: Path, manifest: dict[str, Any]) -> None:
        self.run_dir = run_dir
        self.manifest_path = run_dir / "manifest.json"
        self.checkpoint_path = run_dir / "checkpoints" / "pipeline.json"
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest = manifest
        self.run_id = str(manifest.get("run_id", ""))
        self.runtime = runtime_fingerprint()
        self._resume_identity = resume_fingerprint(self.runtime)
        if self.checkpoint_path.exists():
            try:
                checkpoint = PipelineCheckpoint.model_validate_json(
                    self.checkpoint_path.read_text(encoding="utf-8")
                )
            except (OSError, ValidationError) as exc:
                raise CheckpointMismatchError("Pipeline checkpoint is unreadable") from exc
            if (
                checkpoint.schema_version != 1
                or resume_fingerprint(checkpoint.runtime) != self._resume_identity
            ):
                raise CheckpointMismatchError("Runtime fingerprint differs from checkpoint")
            self.receipts: dict[str, Any] = {
                stage: receipt.model_dump(mode="json")
                for stage, receipt in checkpoint.receipts.items()
            }
        else:
            self.receipts = {}
            self._write_checkpoint()

    def _write_checkpoint(self) -> None:
        atomic_json(
            self.checkpoint_path,
            {
                "schema_version": 1,
                "runtime": self.runtime,
                "receipts": self.receipts,
            },
        )

    def transition(self, state: str) -> None:
        self.manifest["status"] = state
        self.manifest["updated_at"] = utc_now()
        self.manifest["stages"] = self.receipts
        atomic_json(self.manifest_path, self.manifest)

    def stage_started(self, stage: str, inputs: list[Path]) -> float:
        logger.info("stage_started", extra={"run_id": self.run_id, "stage": stage})
        started = time.monotonic()
        self.receipts[stage] = {
            "status": "running",
            "started_at": utc_now(),
            "finished_at": None,
            "runtime": self.runtime,
            "inputs": [self._input_record(path) for path in inputs],
            "outputs": [],
            "metrics": {},
        }
        self._write_checkpoint()
        self.transition(stage)
        return started

    def stage_completed(
        self,
        stage: str,
        started: float,
        outputs: list[Path],
        metrics: dict[str, int | float | str | bool],
    ) -> None:
        receipt = self.receipts[stage]
        receipt.update(
            {
                "status": "completed",
                "finished_at": utc_now(),
                "outputs": [self._record(path) for path in outputs],
                "metrics": {**metrics, "seconds": time.monotonic() - started},
            }
        )
        self._write_checkpoint()
        self.manifest["stages"] = self.receipts
        atomic_json(self.manifest_path, self.manifest)
        logger.info("stage_completed", extra={"run_id": self.run_id, "stage": stage, **metrics})

    def reusable(self, stage: str) -> bool:
        receipt = json_mapping(self.receipts.get(stage))
        if receipt.get("status") != "completed":
            return False
        recorded = {key: str(item) for key, item in json_mapping(receipt.get("runtime")).items()}
        if not recorded or resume_fingerprint(recorded) != self._resume_identity:
            raise CheckpointMismatchError(f"Runtime changed for stage {stage}")
        outputs = json_sequence(receipt.get("outputs"))
        if not outputs:
            raise CheckpointMismatchError(f"Stage {stage} has no output receipt")
        for entry in outputs:
            record = json_mapping(entry)
            path = self._resolve_record(record)
            if (
                not path.is_file()
                or path.stat().st_size != record.get("size_bytes")
                or sha256_file(path) != record.get("sha256")
            ):
                raise ArtifactValidationError(f"Reusable output is corrupt: {path.name}")
        logger.info("artifact_reused", extra={"run_id": self.run_id, "stage": stage})
        return True

    def _record(self, path: Path) -> dict[str, object]:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.run_dir) or resolved.is_symlink():
            raise ArtifactValidationError("Receipt path escapes the run directory")
        return artifact_record(resolved, self.run_dir)

    def _input_record(self, path: Path) -> dict[str, object]:
        resolved = path.resolve()
        if not resolved.is_file() or resolved.is_symlink():
            raise ArtifactValidationError("Receipt input is not a regular file")
        if resolved.is_relative_to(self.run_dir):
            return self._record(resolved)
        return {
            "path": str(resolved),
            "size_bytes": resolved.stat().st_size,
            "sha256": sha256_file(resolved),
        }

    def _resolve_record(self, record: dict[str, object]) -> Path:
        relative = Path(str(record.get("path", "")))
        path = (self.run_dir / relative).resolve()
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not path.is_relative_to(self.run_dir)
            or path.is_symlink()
        ):
            raise ArtifactValidationError("Receipt path escapes the run directory")
        return path


def utc_now() -> str:
    """Return the current instant as a UTC ISO-8601 string.

    Every timestamp written into a run record comes from here, so a manifest, a receipt and a
    report cannot disagree about the clock or the offset they were stamped with.
    """
    return datetime.now(UTC).isoformat()
