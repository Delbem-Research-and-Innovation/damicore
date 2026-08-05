import ast
import json
import re
from pathlib import Path
from typing import cast

import damicore
import damicore_clusterizer
import damicore_distance
import damicore_normalizer
import damicore_tree_builder
import pytest
import tomllib
from damicore.api import VERSION

pytestmark = pytest.mark.contract

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
    return {str(dependency) for dependency in cast(list[object], declared)}


def _classifiers(package: str) -> list[str]:
    declared = _project(package).get("classifiers", [])
    if not isinstance(declared, list):
        return []
    return [str(entry) for entry in cast(list[object], declared)]


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


def test_stage_packages_do_not_import_each_other_or_orchestrator() -> None:
    for stage in STAGES:
        source = ROOT / "packages" / stage / "src" / stage
        for module in source.glob("*.py"):
            forbidden = (STAGES - {stage}) | {"damicore", "synthetic_data"}
            assert not (_imports(module) & forbidden), module


def test_orchestrator_has_no_runtime_dependency_on_synthetic_data() -> None:
    source = ROOT / "packages/damicore/src/damicore"
    for module in source.glob("*.py"):
        assert "synthetic_data" not in _imports(module), module


def test_public_exports_are_exact() -> None:
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


def test_public_result_models_declare_the_specified_fields() -> None:
    """Specification sections 9.3, 18.5 and 18.6 with section 26, which makes a schema part of
    the public API. These two models are the schemas of report.json and of the paths the CLI
    prints, so a field added or renamed here is a contract change and must be a specification
    change first."""
    assert list(damicore.RunReport.model_fields) == [
        "status",
        "failed_stage",
        "object_count",
        "pair_count",
        "community_count",
        "cluster_count",
        "effective_workers",
        "csv_chunk_rows",
        "compression_chunk_bytes",
        "pairs_per_shard",
        "matrix_bytes",
        "required_free_disk_bytes",
        "peak_rss_bytes",
        "ncd_min",
        "ncd_max",
        "ncd_out_of_range_count",
        "negative_branch_count",
        "branch_length_shift",
        "modularity",
        "timings_seconds",
        "verification",
        "warnings",
        "error",
    ]
    assert list(damicore.ArtifactPaths.model_fields) == [
        "run_dir",
        "manifest",
        "report",
        "distance_matrix",
        "labels",
        "tree_json",
        "tree_newick",
        "membership",
        "clusters",
        "normalization_dir",
        "diagnostics_dir",
    ]


def test_public_pyprojects_contain_no_workspace_paths_or_typer() -> None:
    for package in sorted(PUBLIC):
        text = (ROOT / "packages" / package / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        assert "tool.uv.sources" not in text
        assert "typer" not in text.lower()
        assert "click" not in text.lower()
        assert "file://" not in text


def test_third_party_runtime_dependencies_are_exact() -> None:
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


def test_public_packages_declare_one_lockstep_version() -> None:
    """Specification section 26: the five published distributions share one version.

    The version is restated a sixth time in code: `damicore.api.VERSION` is the value `run()`
    stamps into every manifest as `damicore_version`, which section 18.5 makes mandatory run
    provenance. Asserting it here rather than in a test of its own keeps one check total over
    every statement of the released version, so a release bump cannot leave one behind.
    """
    versions = {package: _version(package) for package in sorted(PUBLIC)}
    assert len(set(versions.values())) == 1, versions
    assert re.fullmatch(r"\d+\.\d+\.\d+", versions["damicore"]), versions["damicore"]
    assert VERSION == versions["damicore"], (VERSION, versions["damicore"])


def test_orchestrator_pins_every_stage_within_the_lockstep_minor() -> None:
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


def test_public_packages_support_the_specified_interpreter_range() -> None:
    for package in sorted(PUBLIC):
        assert _project(package)["requires-python"] == ">=3.11,<3.15"


def test_publish_allowlist_matches_the_public_workspace_members() -> None:
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
        and PRIVATE_CLASSIFIER not in _classifiers(directory.name)
    }
    assert set(declared.group(1).split()) == publishable == PUBLIC


def test_every_test_module_declares_a_registered_marker() -> None:
    """AGENTS.md requires a registered marker per suite; prose alone lets new files forget.

    The registered set is read from the root configuration rather than restated, so adding a
    marker there is the only edit needed to make it usable.
    """
    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pytest_options = configuration["tool"]["pytest"]["ini_options"]
    declared_markers = pytest_options["markers"]
    assert isinstance(declared_markers, list)
    registered = {
        str(entry).split(":", 1)[0].strip()
        for entry in cast(list[object], declared_markers)
    }

    modules = sorted(ROOT.glob("packages/*/tests/test_*.py")) + sorted(
        ROOT.glob("tests/*/test_*.py")
    )
    # Guards the discovery: an empty glob would make every assertion below vacuous.
    assert len(modules) >= 11, [str(path) for path in modules]

    unmarked: list[str] = []
    unregistered: list[str] = []
    for path in modules:
        found = re.search(
            r"^pytestmark\s*=\s*pytest\.mark\.(\w+)",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if found is None:
            unmarked.append(str(path.relative_to(ROOT)))
        elif found.group(1) not in registered:
            unregistered.append(f"{path.relative_to(ROOT)}:{found.group(1)}")
    assert not unmarked, unmarked
    assert not unregistered, unregistered


def test_type_check_configuration_covers_every_workspace_package() -> None:
    """Guard the type gate against silently checking nothing.

    `pyrightconfig.json` cannot carry comments, so the reasoning behind its shape lives here:

    - every `include` entry is a concrete path, because a mid-pattern wildcard such as
      `packages/*/src` matches nothing and Pyright then reports success over an empty file
      set, which is how this gate came to analyze zero files;
    - `exclude` is declared explicitly, because Pyright's default excludes every
      dot-directory and would otherwise put `.github/scripts` out of reach;
    - `reportPrivateUsage` is off, because unit tests deliberately exercise internals such as
      the stage-error translation table, and the public surface is asserted instead by
      `test_public_exports_are_exact` above.
    """
    configuration = json.loads(
        (ROOT / "pyrightconfig.json").read_text(encoding="utf-8")
    )
    included = configuration["include"]
    assert isinstance(included, list)
    entries = {str(entry) for entry in cast(list[object], included)}

    for entry in sorted(entries):
        assert "*" not in entry, entry
        assert (ROOT / entry).is_dir(), entry

    for directory in sorted((ROOT / "packages").iterdir()):
        if not (directory / "pyproject.toml").is_file():
            continue
        for area in ("src", "tests"):
            if (directory / area).is_dir():
                relative = f"packages/{directory.name}/{area}"
                assert relative in entries, relative


def test_package_tool_configuration_does_not_drift() -> None:
    """Every workspace member configures Ruff and pytest identically, bar the coverage target.

    `packages/package.mk` exists because "Six copies had already drifted into two variants
    differing only by stray indentation". The same six copies live on in `pyproject.toml`,
    where nothing compares them: a rule added to one package's `select`, a line length raised
    in one `[tool.ruff]`, or a floor lowered in one `addopts` stays invisible until someone
    diffs the files by hand.

    The coverage target is the one value that must differ, so it is normalised away rather
    than restated. A literal template here would make this test a seventh copy of the flag
    list it exists to protect, which is the defect, not the fix.
    """
    members = sorted(
        directory.name
        for directory in (ROOT / "packages").iterdir()
        if (directory / "pyproject.toml").is_file()
    )
    # Guards the discovery: an empty or truncated scan would make every assertion below
    # vacuous. Derived from PUBLIC rather than a literal count, so adding a package is one
    # edit, not two.
    assert set(members) >= PUBLIC, members

    ruff: dict[str, object] = {}
    pytest_options: dict[str, dict[str, object]] = {}
    for member in members:
        with (ROOT / "packages" / member / "pyproject.toml").open("rb") as stream:
            tool = tomllib.load(stream)["tool"]
        options: dict[str, object] = dict(tool["pytest"]["ini_options"])
        addopts = str(options["addopts"])
        # Checked before normalising: otherwise a package measuring another package's
        # coverage would be erased by the substitution instead of caught by it.
        assert re.findall(r"--cov=(\S+)", addopts) == [member], (member, addopts)
        options["addopts"] = addopts.replace(f"--cov={member}", "--cov=<member>")
        ruff[member] = tool["ruff"]
        pytest_options[member] = options

    reference = members[0]
    for member in members[1:]:
        assert ruff[member] == ruff[reference], (member, ruff[member], ruff[reference])
        assert pytest_options[member] == pytest_options[reference], (
            member,
            pytest_options[member],
            pytest_options[reference],
        )
