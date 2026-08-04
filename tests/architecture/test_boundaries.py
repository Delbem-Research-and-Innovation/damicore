import ast
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
    for package in sorted(STAGES | {"damicore"}):
        text = (ROOT / "packages" / package / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        assert "tool.uv.sources" not in text
        assert "typer" not in text.lower()
        assert "click" not in text.lower()
        assert "file://" not in text


def test_runtime_dependencies_and_versions_are_exact():
    expected = {
        "damicore_normalizer": {"pandas>=2.2,<4", "pydantic>=2.10,<3"},
        "damicore_distance": {"numpy>=1.26,<3", "pydantic>=2.10,<3"},
        "damicore_tree_builder": {"numpy>=1.26,<3", "pydantic>=2.10,<3"},
        "damicore_clusterizer": {
            "igraph>=1.0,<1.1",
            "numpy>=1.26,<3",
            "pydantic>=2.10,<3",
        },
        "damicore": {
            "damicore-normalizer>=0.1.0,<0.2.0",
            "damicore-distance>=0.1.0,<0.2.0",
            "damicore-tree-builder>=0.1.0,<0.2.0",
            "damicore-clusterizer>=0.1.0,<0.2.0",
            "pandas>=2.2,<4",
            "pydantic>=2.10,<3",
            "tqdm>=4.66,<5",
        },
    }
    for package, dependencies in expected.items():
        with (ROOT / "packages" / package / "pyproject.toml").open("rb") as stream:
            project = tomllib.load(stream)["project"]
        assert project["version"] == "0.1.0"
        assert project["requires-python"] == ">=3.11,<3.15"
        assert set(project["dependencies"]) == dependencies
