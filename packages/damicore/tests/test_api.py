import hashlib
import json
import os
from pathlib import Path

import pytest

from damicore import (
    ArtifactValidationError,
    ExecutionConfig,
    MaterializationError,
    ResourceLimits,
    estimate,
    load_result,
    run,
)

pytestmark = pytest.mark.unit


def _csv(tmp_path: Path) -> Path:
    path = tmp_path / "input.csv"
    path.write_text("a,b,c\naaaa,aaab,zzzz\naaaa,aaac,zzzy\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("split", ["columns", "rows"])
def test_complete_pipeline_reuse_save_and_load(tmp_path: Path, split: str) -> None:
    source = _csv(tmp_path)
    preview = estimate(source, split=split, execution=ExecutionConfig(workers=1))
    assert preview.within_limits
    output = tmp_path / f"run-{split}"
    result = run(
        source,
        split=split,
        output_dir=output,
        progress=False,
        keep_normalized=True,
        execution=ExecutionConfig(workers=1, pairs_per_shard=1),
    )
    assert result.report.status == "completed"
    assert list(result.membership.columns) == ["object_id", "label", "cluster"]
    assert result.distance_matrix.head(2).shape == (2, 2)
    saved = result.save(tmp_path / f"saved-{split}")
    result.close()
    with pytest.raises(ValueError, match="reload"):
        _ = result.distance_matrix.shape
    loaded = load_result(saved.run_dir)
    loaded.close()
    reused = run(
        source,
        split=split,
        output_dir=output,
        progress=False,
        keep_normalized=True,
        execution=ExecutionConfig(workers=1, pairs_per_shard=1),
    )
    reused.close()


def test_limits_materialization_and_corruption(tmp_path: Path) -> None:
    source = _csv(tmp_path)
    limited = estimate(
        source,
        execution=ExecutionConfig(
            workers=1,
            limits=ResourceLimits(max_objects=2),
        ),
    )
    assert limited.violations[0] == "max_objects"

    output = tmp_path / "run"
    result = run(
        source,
        output_dir=output,
        progress=False,
        execution=ExecutionConfig(workers=1, pandas_materialization_limit_bytes=1),
    )
    with pytest.raises(MaterializationError, match="head"):
        result.distance_matrix.to_pandas()
    result.close()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    (output / "tree.nwk").write_text("corrupt", encoding="utf-8")
    with pytest.raises(ArtifactValidationError):
        load_result(output)


@pytest.mark.parametrize("malicious_path", ["../escape.bin", "/tmp/escape.bin"])
def test_save_rejects_manifest_paths_outside_roots(tmp_path: Path, malicious_path: str) -> None:
    output = tmp_path / "run"
    result = run(
        _csv(tmp_path),
        output_dir=output,
        progress=False,
        execution=ExecutionConfig(workers=1),
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key = next(iter(manifest["artifacts"]))
    record = manifest["artifacts"].pop(key)
    record["path"] = malicious_path
    manifest["artifacts"][malicious_path] = record
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    destination = tmp_path / "exports" / "saved"
    with pytest.raises(ArtifactValidationError, match="manifest is invalid"):
        result.save(destination)
    assert not destination.exists()
    result.close()


def test_save_revalidates_artifact_bytes_and_symlinks(tmp_path: Path) -> None:
    output = tmp_path / "run"
    result = run(
        _csv(tmp_path),
        output_dir=output,
        progress=False,
        execution=ExecutionConfig(workers=1),
    )
    tree_path = output / "tree.nwk"
    original_tree = tree_path.read_bytes()
    tree_path.write_text("tampered;", encoding="utf-8")
    destination = tmp_path / "saved-tampered"
    with pytest.raises(ArtifactValidationError, match="hash or size"):
        result.save(destination)
    assert not (destination / "tree.nwk").exists()
    tree_path.write_bytes(original_tree)

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    external = tmp_path / "external.bin"
    external.write_bytes(b"external")
    link = output / "external-link"
    os.symlink(external, link)
    record = {
        "path": "external-link",
        "size_bytes": external.stat().st_size,
        "sha256": hashlib.sha256(external.read_bytes()).hexdigest(),
    }
    manifest["artifacts"]["external-link"] = record
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="escapes"):
        result.save(tmp_path / "saved-link")
    result.close()


def test_load_result_rejects_extra_manifest_fields(tmp_path: Path) -> None:
    output = tmp_path / "run"
    result = run(
        _csv(tmp_path),
        output_dir=output,
        progress=False,
        execution=ExecutionConfig(workers=1),
    )
    result.close()
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    extended = {**manifest, "unexpected": True}
    manifest_path.write_text(json.dumps(extended), encoding="utf-8")
    with pytest.raises(ArtifactValidationError):
        load_result(output)

    manifest["artifacts"].pop("tree.nwk")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError):
        load_result(output)
