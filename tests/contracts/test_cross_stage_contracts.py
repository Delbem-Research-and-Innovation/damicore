"""Cross-stage artifact contracts and verification invariants (specification sections 17, 24.2)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from damicore import (
    ArtifactValidationError,
    CheckpointMismatchError,
    ExecutionConfig,
    api,
    run,
)
from damicore.pipeline import (
    RESUME_FINGERPRINT_KEYS,
    resume_fingerprint,
    runtime_fingerprint,
)
from synthetic_data import generate_csv

pytestmark = pytest.mark.contract

SERIAL = ExecutionConfig(workers=1)


def _completed_run(directory: Path) -> Path:
    source = generate_csv(
        directory / "dataset.csv", rows=24, columns=8, clusters=2, seed=42
    )
    run_dir = directory / "run"
    result = run(
        source,
        output_dir=run_dir,
        keep_normalized=True,
        progress=False,
        execution=SERIAL,
    )
    result.close()
    return run_dir


def test_labels_agree_across_producer_and_consumers(tmp_path: Path) -> None:
    run_dir = _completed_run(tmp_path)
    normalization = json.loads(
        (run_dir / "normalization/manifest.json").read_text("utf-8")
    )
    labels = json.loads((run_dir / "labels.json").read_text("utf-8"))
    tree = json.loads((run_dir / "tree.json").read_text("utf-8"))
    clusters = json.loads((run_dir / "clusters.json").read_text("utf-8"))

    normalized_ids = [item["object_id"] for item in normalization["objects"]]
    leaf_ids = [node["id"] for node in tree["nodes"] if node["kind"] == "leaf"]
    clustered_ids = [
        oid for group in clusters["clusters"] for oid in group["object_ids"]
    ]

    assert list(labels["object_ids"]) == normalized_ids
    assert set(leaf_ids) == set(normalized_ids)
    assert set(clustered_ids) == set(normalized_ids)


def test_cross_verification_rejects_inconsistent_membership(tmp_path: Path) -> None:
    run_dir = _completed_run(tmp_path)
    normalization = api._load_normalization(run_dir / "normalization/manifest.json")
    membership_path = run_dir / "membership.csv"
    with membership_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows[0]["cluster"] = "999"  # assignment no longer matches clusters.json
    with membership_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["object_id", "label", "cluster"])
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ArtifactValidationError):
        api._verify_cross_artifacts(run_dir, normalization, None, 0)


def test_resume_fingerprint_projects_only_the_compat_subset() -> None:
    full = runtime_fingerprint()
    assert set(resume_fingerprint(full)) == set(RESUME_FINGERPRINT_KEYS)
    assert "platform" not in resume_fingerprint(full)

    environment_noise = {**full, "platform": "other", "pandas": "0.0", "tqdm": "0.0"}
    assert resume_fingerprint(environment_noise) == resume_fingerprint(full)

    incompatible = {**full, "numpy": "0.0.0"}
    assert resume_fingerprint(incompatible) != resume_fingerprint(full)


def test_incomplete_run_resumes_despite_environment_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = generate_csv(
        tmp_path / "dataset.csv", rows=24, columns=8, clusters=2, seed=42
    )
    run_dir = tmp_path / "run"

    def fail_cluster(*_args: object, **_kwargs: object) -> object:
        raise api.ClusterizerError("injected", code="clusterization_error")

    monkeypatch.setattr(api, "cluster_tree", fail_cluster)
    with pytest.raises(api.ClusterizationError):
        run(source, output_dir=run_dir, progress=False, execution=SERIAL)

    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    manifest["runtime"]["platform"] = "a-completely-different-platform"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.undo()
    resumed = run(source, output_dir=run_dir, progress=False, execution=SERIAL)
    try:
        assert resumed.report.status == "completed"
    finally:
        resumed.close()


def test_incomplete_run_rejects_incompatible_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = generate_csv(
        tmp_path / "dataset.csv", rows=24, columns=8, clusters=2, seed=42
    )
    run_dir = tmp_path / "run"

    def fail_cluster(*_args: object, **_kwargs: object) -> object:
        raise api.ClusterizerError("injected", code="clusterization_error")

    monkeypatch.setattr(api, "cluster_tree", fail_cluster)
    with pytest.raises(api.ClusterizationError):
        run(source, output_dir=run_dir, progress=False, execution=SERIAL)

    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    manifest["runtime"]["numpy"] = "0.0.0"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.undo()
    with pytest.raises(CheckpointMismatchError):
        run(source, output_dir=run_dir, progress=False, execution=SERIAL)
