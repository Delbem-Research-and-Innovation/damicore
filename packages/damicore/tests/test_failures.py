import json

import pytest
from damicore_clusterizer import ClusterizerError
from damicore_distance import DistanceError
from damicore_normalizer import NormalizerError
from damicore_tree_builder import TreeBuilderError

import damicore.api as api
from damicore import (
    ArtifactValidationError,
    ConfigurationError,
    ExecutionConfig,
    OutputDirectoryConflictError,
    ResourceLimitError,
    estimate,
    load_result,
    run,
)
from damicore.errors import (
    CompressionError,
    CSVFormatError,
    DistanceMatrixValidationError,
    InputValidationError,
    TreeFormatError,
)
from damicore.progress import distance_progress


def _csv(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("a,b,c\naa,ab,zz\naa,ac,zy\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"split": "invalid"}, "split"),
        ({"delimiter": "::"}, "delimiter"),
        ({"encoding": "not-an-encoding"}, "encoding"),
    ],
)
def test_invalid_configuration_fails_before_csv_read(tmp_path, kwargs, message):
    missing = tmp_path / "missing.csv"
    with pytest.raises(ConfigurationError, match=message):
        estimate(missing, **kwargs)


def test_run_rejects_limits_and_conflicting_directories(tmp_path):
    source = _csv(tmp_path)
    with pytest.raises(ResourceLimitError):
        run(
            source,
            output_dir=tmp_path / "limited",
            progress=False,
            execution=ExecutionConfig(workers=1, limits={"max_objects": 2}),
        )
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "user.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(OutputDirectoryConflictError):
        run(source, output_dir=occupied, progress=False, execution=ExecutionConfig(workers=1))
    assert (occupied / "user.txt").read_text(encoding="utf-8") == "keep"


def test_failed_stage_is_reported_and_resumed(tmp_path, monkeypatch):
    source = _csv(tmp_path)
    output = tmp_path / "resume"
    original = api.cluster_tree

    def fail_cluster(*_args, **_kwargs):
        raise ClusterizerError("injected failure", code="clusterization_error")

    monkeypatch.setattr(api, "cluster_tree", fail_cluster)
    with pytest.raises(api.ClusterizationError):
        run(source, output_dir=output, progress=False, execution=ExecutionConfig(workers=1))
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["failed_stage"] == "clusterizing"

    monkeypatch.setattr(api, "cluster_tree", original)
    result = run(source, output_dir=output, progress=False, execution=ExecutionConfig(workers=1))
    assert result.report.status == "completed"
    result.close()


def test_reuse_flags_and_loader_terminal_state(tmp_path):
    source = _csv(tmp_path)
    output = tmp_path / "run"
    result = run(source, output_dir=output, progress=False, execution=ExecutionConfig(workers=1))
    with pytest.raises(OutputDirectoryConflictError, match="reuse"):
        run(
            source,
            output_dir=output,
            progress=False,
            execution=ExecutionConfig(workers=1, reuse_completed=False),
        )
    with pytest.raises(OutputDirectoryConflictError):
        result.save(tmp_path)
    result.close()

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "failed"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="completed"):
        load_result(output)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (NormalizerError("csv", code="csv_format_error"), CSVFormatError),
        (NormalizerError("drift", code="input_drift"), InputValidationError),
        (NormalizerError("normal", code="normalization_error"), api.NormalizationError),
        (DistanceError("compress", code="compression_error"), CompressionError),
        (
            DistanceError("matrix", code="distance_matrix_validation_error"),
            DistanceMatrixValidationError,
        ),
        (DistanceError("distance"), api.DistanceComputationError),
        (TreeBuilderError("tree", code="tree_format_error"), TreeFormatError),
        (TreeBuilderError("build"), api.TreeBuildError),
        (
            TreeBuilderError("conflict", code="output_directory_conflict_error"),
            OutputDirectoryConflictError,
        ),
        (
            TreeBuilderError("artifact", code="artifact_validation_error"),
            ArtifactValidationError,
        ),
        (ClusterizerError("tree", code="tree_format_error"), TreeFormatError),
        (ClusterizerError("cluster"), api.ClusterizationError),
        (
            ClusterizerError("conflict", code="output_directory_conflict_error"),
            OutputDirectoryConflictError,
        ),
        (ValueError("unknown"), api.DamicoreError),
    ],
)
def test_stage_error_translation(error, expected):
    assert isinstance(api._translated_stage_error(error), expected)


def test_progress_adapter_enabled_and_disabled():
    callback, close = distance_progress(False)
    assert callback is None
    close()
    callback, close = distance_progress(True)
    assert callback is not None
    callback(1, 2, "distance")
    close()
