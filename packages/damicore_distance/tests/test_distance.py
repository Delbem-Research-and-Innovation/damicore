import json

import numpy as np
import pytest
from damicore_normalizer import NormalizationConfig, normalize_csv

import damicore_distance.api as distance_api
from damicore_distance import (
    DistanceConfig,
    DistanceError,
    DistanceMatrixView,
    compute_distance_matrix,
)
from damicore_distance.ncd import normalized_compression_distance


def _normalized(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("a,b,c\naaaa,aaab,zzzz\naaaa,aaab,zzzy\n", encoding="utf-8")
    return normalize_csv(
        source,
        tmp_path / "normalized",
        config=NormalizationConfig(chunk_rows=1),
    )


def test_ncd_is_not_clamped_and_zero_denominator_fails():
    assert normalized_compression_distance(10, 20, 50) == 2.0
    with pytest.raises(DistanceError, match="denominator"):
        normalized_compression_distance(0, 0, 1)


def test_serial_parallel_and_resumed_are_bitwise_equal(tmp_path):
    normalized = _normalized(tmp_path)
    serial = compute_distance_matrix(
        normalized.manifest_path,
        tmp_path / "serial",
        config=DistanceConfig(workers=1, pairs_per_shard=1),
    )
    parallel = compute_distance_matrix(
        normalized.manifest_path,
        tmp_path / "parallel",
        config=DistanceConfig(workers=2, pairs_per_shard=1),
    )
    resumed = compute_distance_matrix(
        normalized.manifest_path,
        tmp_path / "serial",
        config=DistanceConfig(workers=1, pairs_per_shard=1),
    )
    serial_matrix = np.load(serial.matrix_path, allow_pickle=False)
    assert serial_matrix.dtype == np.float64
    assert np.array_equal(serial_matrix, np.load(parallel.matrix_path, allow_pickle=False))
    assert np.array_equal(serial_matrix, np.load(resumed.matrix_path, allow_pickle=False))


def test_diagnostics_and_corruption_detection(tmp_path):
    normalized = _normalized(tmp_path)
    result = compute_distance_matrix(
        normalized.manifest_path,
        tmp_path / "run",
        config=DistanceConfig(workers=1, save_diagnostics=True),
    )
    assert result.pair_count == 3
    assert (tmp_path / "run/diagnostics/distance.csv").is_file()
    assert (tmp_path / "run/diagnostics/ncd-pairs.csv").is_file()

    manifest = json.loads(normalized.manifest_path.read_text(encoding="utf-8"))
    object_path = normalized.manifest_path.parent / manifest["objects"][0]["relative_path"]
    object_path.write_bytes(object_path.read_bytes() + b"corrupt")
    with pytest.raises(DistanceError, match="hash or size"):
        compute_distance_matrix(normalized.manifest_path, tmp_path / "corrupt")


def test_gzip_progress_view_and_resume_guards(tmp_path):
    normalized = _normalized(tmp_path)
    calls = []
    result = compute_distance_matrix(
        normalized.manifest_path,
        tmp_path / "gzip",
        config=DistanceConfig(compressor="gzip", workers=1, pairs_per_shard=2),
        progress=lambda completed, total, message: calls.append((completed, total, message)),
    )
    assert calls[-1] == (3, 3, "distance")
    view = DistanceMatrixView(result.matrix_path, ["a", "b", "c"])
    assert float(view[0, 0]) == 0.0
    assert view.to_pandas(force=True).shape == (3, 3)
    view.close()
    with pytest.raises(ValueError, match="reload"):
        view.head()
    with pytest.raises(DistanceError, match="resume is disabled"):
        compute_distance_matrix(
            normalized.manifest_path,
            tmp_path / "gzip",
            config=DistanceConfig(compressor="gzip", workers=1, resume=False),
        )


def test_manifest_and_checkpoint_corruption_fail(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")
    with pytest.raises(DistanceError, match="manifest"):
        compute_distance_matrix(bad, tmp_path / "bad-run")

    normalized = _normalized(tmp_path)
    output = tmp_path / "run"
    compute_distance_matrix(
        normalized.manifest_path,
        output,
        config=DistanceConfig(workers=1, pairs_per_shard=1),
    )
    checkpoint = output / "checkpoints/compressed-sizes.json"
    checkpoint.write_text("broken", encoding="utf-8")
    with pytest.raises(DistanceError, match="checkpoint"):
        compute_distance_matrix(
            normalized.manifest_path,
            output,
            config=DistanceConfig(workers=1, pairs_per_shard=1),
        )


def test_manifest_schema_rejects_extra_fields(tmp_path):
    normalized = _normalized(tmp_path)
    manifest = json.loads(normalized.manifest_path.read_text(encoding="utf-8"))
    manifest["unexpected"] = True
    normalized.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(DistanceError, match="manifest"):
        compute_distance_matrix(normalized.manifest_path, tmp_path / "invalid-schema")


def test_resume_rejects_symmetric_finite_matrix_corruption(tmp_path):
    normalized = _normalized(tmp_path)
    output = tmp_path / "run"
    result = compute_distance_matrix(
        normalized.manifest_path,
        output,
        config=DistanceConfig(workers=1, pairs_per_shard=1),
    )
    matrix = np.load(result.matrix_path, mmap_mode="r+", allow_pickle=False)
    matrix[0, 1] = matrix[1, 0] = float(matrix[0, 1]) + 0.125
    matrix.flush()
    del matrix
    with pytest.raises(DistanceError, match="digest"):
        compute_distance_matrix(
            normalized.manifest_path,
            output,
            config=DistanceConfig(workers=1, pairs_per_shard=1),
        )


@pytest.mark.parametrize("fail_after", [0, 1, 2])
def test_resume_after_each_shard_boundary_matches_clean_run(tmp_path, monkeypatch, fail_after):
    normalized = _normalized(tmp_path)
    config = DistanceConfig(workers=1, pairs_per_shard=1)
    clean = compute_distance_matrix(normalized.manifest_path, tmp_path / "clean", config=config)
    original_worker = distance_api._worker
    calls = 0

    def fail_at_boundary(arguments):
        nonlocal calls
        if calls == fail_after:
            raise RuntimeError("injected shard interruption")
        calls += 1
        return original_worker(arguments)

    monkeypatch.setattr(distance_api, "_worker", fail_at_boundary)
    interrupted = tmp_path / f"interrupted-{fail_after}"
    with pytest.raises(RuntimeError, match="injected"):
        compute_distance_matrix(normalized.manifest_path, interrupted, config=config)
    monkeypatch.setattr(distance_api, "_worker", original_worker)

    resumed = compute_distance_matrix(normalized.manifest_path, interrupted, config=config)
    assert np.array_equal(
        np.load(clean.matrix_path, allow_pickle=False),
        np.load(resumed.matrix_path, allow_pickle=False),
    )
