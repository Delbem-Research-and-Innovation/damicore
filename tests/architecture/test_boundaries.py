import ast
import re
from pathlib import Path

import damicore
import damicore_clusterizer
import damicore_distance
import damicore_normalizer
import damicore_tree_builder
import tomllib

ROOT = Path(__file__).parents[2]
STAGES = {
    "damicore_normalizer",
    "damicore_distance",
    "damicore_tree_builder",
    "damicore_clusterizer",
}
PUBLIC = STAGES | {"damicore"}

# A workspace member carrying this classifier is private test infrastructure and must never
# be published (specification section 9.3).
PRIVATE_CLASSIFIER = "Private :: Do Not Upload"


def _project(package: str) -> dict[str, object]:
    with (ROOT / "packages" / package / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]


def _version(package: str) -> str:
    return str(_project(package)["version"])


def _dependencies(package: str) -> set[str]:
    declared = _project(package)["dependencies"]
    assert isinstance(declared, list)
    return {str(dependency) for dependency in declared}


def _release(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_stage_packages_do_not_import_each_other_or_orchestrator():
    for stage in STAGES:
        source = ROOT / "packages" / stage / "src" / stage
        for module in source.glob("*.py"):
            forbidden = (STAGES - {stage}) | {"damicore", "synthetic_data"}
            assert not (_imports(module) & forbidden), module


def test_orchestrator_has_no_runtime_dependency_on_synthetic_data():
    source = ROOT / "packages/damicore/src/damicore"
    for module in source.glob("*.py"):
        assert "synthetic_data" not in _imports(module), module


def test_public_exports_are_exact():
    assert damicore_normalizer.__all__ == [
        "normalize_csv",
        "NormalizationConfig",
        "NormalizationResult",
        "ObjectDescriptor",
        "NormalizerError",
    ]
    assert damicore_distance.__all__ == [
        "compute_distance_matrix",
        "DistanceConfig",
        "DistanceResult",
        "DistanceMatrixView",
        "DistanceError",
    ]
    assert damicore_tree_builder.__all__ == [
        "build_tree",
        "neighbor_joining",
        "TreeBuildConfig",
        "TreeBuildResult",
        "Tree",
        "TreeNode",
        "TreeEdge",
        "TreeBuilderError",
    ]
    assert damicore_clusterizer.__all__ == [
        "cluster_tree",
        "ClusterConfig",
        "ClusterResult",
        "ClusterizerError",
    ]
    assert set(damicore.__all__) == {
        "run",
        "estimate",
        "load_result",
        "DamicoreResult",
        "DistanceMatrixView",
        "ExecutionConfig",
        "ResourceLimits",
        "ResourceEstimate",
        "RunReport",
        "ArtifactPaths",
        "DamicoreError",
        "ConfigurationError",
        "InputValidationError",
        "CSVFormatError",
        "ResourceLimitError",
        "OutputDirectoryConflictError",
        "CheckpointMismatchError",
        "NormalizationError",
        "CompressionError",
        "DistanceComputationError",
        "DistanceMatrixValidationError",
        "TreeBuildError",
        "TreeFormatError",
        "ClusterizationError",
        "ArtifactValidationError",
        "MaterializationError",
    }


def test_public_pyprojects_contain_no_workspace_paths_or_typer():
    for package in sorted(PUBLIC):
        text = (ROOT / "packages" / package / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        assert "tool.uv.sources" not in text
        assert "typer" not in text.lower()
        assert "click" not in text.lower()
        assert "file://" not in text


def test_third_party_runtime_dependencies_are_exact():
    """Specification section 8.2 closes the runtime dependency set and its ranges."""
    expected = {
        "damicore_normalizer": {"pandas>=2.2,<4", "pydantic>=2.10,<3"},
        "damicore_distance": {"numpy>=1.26,<3", "pydantic>=2.10,<3"},
        "damicore_tree_builder": {"numpy>=1.26,<3", "pydantic>=2.10,<3"},
        "damicore_clusterizer": {
            "igraph>=1.0,<1.1",
            "numpy>=1.26,<3",
            "pydantic>=2.10,<3",
        },
        "damicore": {"pandas>=2.2,<4", "pydantic>=2.10,<3", "tqdm>=4.66,<5"},
    }
    for package, dependencies in expected.items():
        third_party = {
            dependency
            for dependency in _dependencies(package)
            if not dependency.startswith("damicore-")
        }
        assert third_party == dependencies, package


def test_public_packages_declare_one_lockstep_version():
    """Specification section 26: the five published distributions share one version."""
    versions = {package: _version(package) for package in sorted(PUBLIC)}
    assert len(set(versions.values())) == 1, versions
    assert re.fullmatch(r"\d+\.\d+\.\d+", versions["damicore"]), versions["damicore"]


def test_orchestrator_pins_every_stage_within_the_lockstep_minor():
    """A published damicore must resolve stage packages of its own compatible release.

    The bound is asserted relative to the declared version rather than against a literal,
    so a release bump does not have to be mirrored here.
    """
    version = _version("damicore")
    major, minor, _ = _release(version)
    # Specification section 26: during 0.x an incompatible change increments the minor, so
    # the compatible range is capped at the next minor rather than the next major.
    ceiling = f"<{major}.{minor + 1}.0"

    pinned: dict[str, str] = {}
    for dependency in _dependencies("damicore"):
        if not dependency.startswith("damicore-"):
            continue
        name, _, specifier = dependency.partition(">=")
        floor, _, cap = specifier.partition(",")
        assert cap == ceiling, dependency
        assert _release(floor) <= _release(version), dependency
        pinned[name] = dependency

    assert set(pinned) == {stage.replace("_", "-") for stage in STAGES}


def test_public_packages_support_the_specified_interpreter_range():
    for package in sorted(PUBLIC):
        assert _project(package)["requires-python"] == ">=3.11,<3.15"


def test_publish_allowlist_matches_the_public_workspace_members():
    """The Makefile allowlist is what CI builds; drifting from the workspace is a defect.

    Keeping the allowlist explicit means a new package cannot become publishable by
    accident; this test means it also cannot be silently forgotten.
    """
    declared = re.search(
        r"^PUBLIC_PACKAGES\s*:=\s*(.+)$",
        (ROOT / "Makefile").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert declared is not None, "Makefile declares no PUBLIC_PACKAGES"

    publishable = {
        directory.name
        for directory in (ROOT / "packages").iterdir()
        if (directory / "pyproject.toml").is_file()
        and PRIVATE_CLASSIFIER not in _project(directory.name).get("classifiers", [])
    }
    assert set(declared.group(1).split()) == publishable == PUBLIC
