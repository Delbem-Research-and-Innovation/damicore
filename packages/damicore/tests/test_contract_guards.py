"""Guards that back the specification's public contracts: the CLI exit-status table, the
configuration bounds, the preflight input checks, and the manifest's own narrowing helpers."""

import os
from importlib import import_module
from pathlib import Path

import pytest

from damicore import (
    ArtifactValidationError,
    CheckpointMismatchError,
    ConfigurationError,
    CSVFormatError,
    DamicoreError,
    ExecutionConfig,
    InputValidationError,
    OutputDirectoryConflictError,
    ResourceLimitError,
    estimate,
)
from damicore.cli import _exit_code
from damicore.manifest import atomic_json, json_mapping, json_sequence

pytestmark = pytest.mark.unit


# Specification section 19 maps every public failure onto a CLI exit status. The table is the
# contract a shell script depends on, so each row pins one status rather than the mapping
# being re-derived from the class hierarchy at review time.
EXIT_STATUS_TABLE = [
    pytest.param(ConfigurationError("bad"), 2, id="configuration-error"),
    pytest.param(InputValidationError("bad"), 2, id="input-validation-error"),
    pytest.param(CSVFormatError("bad"), 2, id="csv-format-error-inherits-input"),
    pytest.param(ResourceLimitError("bad"), 3, id="resource-limit-error"),
    pytest.param(ArtifactValidationError("bad"), 4, id="artifact-validation-error"),
    pytest.param(OutputDirectoryConflictError("bad"), 5, id="output-directory-conflict"),
    pytest.param(CheckpointMismatchError("bad"), 5, id="checkpoint-mismatch"),
    pytest.param(DamicoreError("bad"), 4, id="unclassified-falls-back-to-four"),
]


@pytest.mark.parametrize(("error", "status"), EXIT_STATUS_TABLE)
def test_every_public_failure_maps_to_its_documented_exit_status(
    error: DamicoreError, status: int
) -> None:
    assert _exit_code(error) == status


def test_workers_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        ExecutionConfig(workers=0)


def test_estimate_rejects_a_path_that_is_not_a_regular_file(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError, match="readable regular file"):
        estimate(tmp_path / "absent.csv")


def test_estimate_detects_a_csv_changed_underneath_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preflight hashes and then scans the CSV; if it changes between those reads the
    estimate would describe an input the run will never see."""
    # `damicore.estimate` the submodule is shadowed by the re-exported function of the same
    # name, so plain `import damicore.estimate as m` would bind the function instead.
    estimate_module = import_module("damicore.estimate")

    source = tmp_path / "input.csv"
    source.write_text("a,b\n1,2\n2,3\n", encoding="utf-8")
    real_hash = estimate_module._hash

    def mutating_hash(path: Path) -> str:
        digest = real_hash(path)
        source.write_text("a,b\n1,2\n2,3\n4,5\n", encoding="utf-8")
        return digest

    monkeypatch.setattr(estimate_module, "_hash", mutating_hash)
    with pytest.raises(InputValidationError, match="changed during preflight") as raised:
        estimate(source)
    assert raised.value.code == "input_drift"


# Both helpers narrow a value decoded from JSON, where any type is possible.
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("a string", [], id="string-is-not-a-sequence"),
        pytest.param({"k": "v"}, [], id="mapping-is-not-a-sequence"),
        pytest.param(None, [], id="null-is-not-a-sequence"),
        pytest.param([1, 2], [1, 2], id="list-passes-through"),
    ],
)
def test_json_sequence_narrows_any_decoded_value(value: object, expected: list[object]) -> None:
    assert json_sequence(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("a string", {}, id="string-is-not-a-mapping"),
        pytest.param([1], {}, id="list-is-not-a-mapping"),
        pytest.param({"k": "v"}, {"k": "v"}, id="mapping-passes-through"),
    ],
)
def test_json_mapping_narrows_any_decoded_value(value: object, expected: dict[str, object]) -> None:
    assert json_mapping(value) == expected


def test_a_failed_manifest_write_leaves_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing_replace(src: object, dst: object) -> None:
        raise OSError("simulated failure while committing the manifest")

    monkeypatch.setattr(os, "replace", failing_replace)
    target = tmp_path / "manifest.json"
    with pytest.raises(OSError):
        atomic_json(target, {"a": 1})
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
