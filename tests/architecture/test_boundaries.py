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
# be published.
PRIVATE_CLASSIFIER = "Private :: Do Not Upload"


def _project(package: str) -> dict[str, object]:
    with (ROOT / "packages" / package / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]


def _tool(path: Path) -> dict[str, object]:
    with path.open("rb") as stream:
        return tomllib.load(stream)["tool"]


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


# rglob, not glob: every package is flat today, so a top-level scan happens to see every
# module. The day one grows a subpackage, glob would keep passing while checking nothing.
def test_stage_packages_do_not_import_each_other_or_orchestrator() -> None:
    for stage in STAGES:
        source = ROOT / "packages" / stage / "src" / stage
        modules = [path for path in source.rglob("*.py") if "__pycache__" not in path.parts]
        assert modules, stage
        for module in modules:
            forbidden = (STAGES - {stage}) | {"damicore", "synthetic_data"}
            assert not (_imports(module) & forbidden), module


def test_orchestrator_has_no_runtime_dependency_on_synthetic_data() -> None:
    source = ROOT / "packages/damicore/src/damicore"
    modules = [path for path in source.rglob("*.py") if "__pycache__" not in path.parts]
    assert modules
    for module in modules:
        assert "synthetic_data" not in _imports(module), module


def test_public_exports_are_exact() -> None:
    assert damicore_normalizer.__all__ == [
        "materialize_objects",
        "normalize_csv",
        "NormalizationConfig",
        "DelimitedSource",
        "SpreadsheetSource",
        "FileCorpusSource",
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
        "DatasetFormatError",
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
    """A published schema is part of the public API. These two models are the schemas of
    report.json and of the paths the CLI prints, so a field added or renamed here is a
    contract change and needs a version bump, not an edit to this list."""
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
        text = (ROOT / "packages" / package / "pyproject.toml").read_text(encoding="utf-8")
        assert "tool.uv.sources" not in text
        assert "typer" not in text.lower()
        assert "click" not in text.lower()
        assert "file://" not in text


# PyPI freezes metadata per version: a missing key is not a fix, it is a version number. These
# fields are also the only ones nothing else in the repository reads, so without this they are
# unverified by construction. The assertions are about presence and shape, never the text of a
# field, so ordinary editing stays free.
REQUIRED_URLS = frozenset({"Homepage", "Repository", "Issues", "Documentation", "Changelog"})
SHARED_CLASSIFIERS = frozenset(
    {
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Typing :: Typed",
    }
)


def _urls(package: str) -> dict[str, str]:
    declared = _project(package).get("urls", {})
    if not isinstance(declared, dict):
        return {}
    return {str(key): str(value) for key, value in cast(dict[str, object], declared).items()}


@pytest.mark.parametrize("package", sorted(PUBLIC))
def test_every_public_package_carries_navigable_pypi_metadata(package: str) -> None:
    urls = _urls(package)
    assert REQUIRED_URLS <= set(urls), package
    # The project declares no routable mailbox, so Issues is the contact channel and every
    # link has to actually resolve as one.
    assert all(value.startswith("https://") for value in urls.values()), urls
    assert SHARED_CLASSIFIERS <= set(_classifiers(package)), package
    keywords = _project(package).get("keywords", [])
    assert isinstance(keywords, list)
    assert keywords, package


def test_every_public_package_ships_the_typing_marker_it_advertises() -> None:
    """`Typing :: Typed` is a claim; py.typed is what makes it true. Asserting the classifier
    without the file would let the distributions advertise types they do not deliver."""
    for package in sorted(PUBLIC):
        marker = ROOT / "packages" / package / "src" / package / "py.typed"
        assert marker.is_file(), package


def test_third_party_runtime_dependencies_are_exact() -> None:
    """The runtime dependency set and its ranges are closed; this test is what closes them.

    Each set is exactly what its distribution imports: a dependency reached only through
    another package is not declared, and one that is imported directly is, even when a
    sibling would have supplied it anyway. damicore imports numpy in api.py, so it declares
    numpy rather than relying on the stage packages; damicore_clusterizer builds its graphs
    through igraph alone, so it declares none.
    """
    expected = {
        "damicore_normalizer": {
            "openpyxl>=3.1,<4",
            "pandas>=2.2,<4",
            "pydantic>=2.10,<3",
        },
        "damicore_distance": {"numpy>=1.26,<3", "pydantic>=2.10,<3"},
        "damicore_tree_builder": {"numpy>=1.26,<3", "pydantic>=2.10,<3"},
        "damicore_clusterizer": {"igraph>=1.0,<1.1", "pydantic>=2.10,<3"},
        "damicore": {
            "numpy>=1.26,<3",
            "pandas>=2.2,<4",
            "pydantic>=2.10,<3",
            "tqdm>=4.66,<5",
        },
    }
    for package, dependencies in expected.items():
        third_party = {
            dependency
            for dependency in _dependencies(package)
            if not dependency.startswith("damicore-")
        }
        assert third_party == dependencies, package


def _optional_dependencies(package: str) -> dict[str, set[str]]:
    declared = _project(package).get("optional-dependencies", {})
    if not isinstance(declared, dict):
        return {}
    return {
        str(extra): {str(entry) for entry in cast(list[object], entries)}
        for extra, entries in cast(dict[str, object], declared).items()
        if isinstance(entries, list)
    }


def test_optional_dependency_extras_are_exact() -> None:
    """The extras are closed as well as the required set.

    The check above reads only `[project.dependencies]`, so an extra is invisible to it: one
    could be added, or silently widened, without any assertion noticing. damicore-distance's
    pandas extra is what makes head() and to_pandas() optional, so its range is a contract.
    """
    expected: dict[str, dict[str, set[str]]] = {
        "damicore_normalizer": {},
        "damicore_distance": {"pandas": {"pandas>=2.2,<4"}},
        "damicore_tree_builder": {},
        "damicore_clusterizer": {},
        "damicore": {},
    }
    for package, extras in expected.items():
        assert _optional_dependencies(package) == extras, package


def test_the_aggregate_requires_the_pandas_extra_of_the_distance_package() -> None:
    """`pip install damicore` has to bring pandas with it: the documented quickstart calls
    result.distance_matrix.head(). Depending on the bare distribution would leave that
    example raising at runtime while every wheel still resolved and installed cleanly."""
    version = _version("damicore")
    major, minor, _ = _release(version)
    ceiling = f"<{major}.{minor + 1}.0"
    assert f"damicore-distance[pandas]>={version},{ceiling}" in _dependencies("damicore")


def test_public_packages_declare_one_lockstep_version() -> None:
    """The five published distributions share one version.

    The version is restated a sixth time in code: `damicore.api.VERSION` is the value `run()`
    stamps into every manifest as `damicore_version`, which is mandatory run
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
    # During 0.x an incompatible change increments the minor, so
    # the compatible range is capped at the next minor rather than the next major.
    ceiling = f"<{major}.{minor + 1}.0"

    pinned: dict[str, str] = {}
    for dependency in _dependencies("damicore"):
        if not dependency.startswith("damicore-"):
            continue
        name, _, specifier = dependency.partition(">=")
        # An extra qualifies the requirement, not the distribution: damicore-distance[pandas]
        # is still the damicore-distance release this pin has to bound.
        name = name.partition("[")[0]
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


def test_the_aggregate_publishes_only_after_the_stages_it_depends_on() -> None:
    """`damicore` requires the four stage distributions within its own release, so it must
    reach an index only once they are on it.

    Publishing all five as one matrix left them unordered, and the 0.1.0 release put
    `damicore` on PyPI eleven minutes before `damicore-tree-builder`; for those eleven
    minutes `pip install damicore` could not resolve. Merging the two publish jobs back
    together would restore that window silently, because no other check reads the workflow.

    Parsed by hand rather than with a YAML library: PyYAML reaches this environment only as
    a transitive dependency of pre-commit, and depending on one of those undeclared is the
    same defect this suite exists to catch.
    """
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    blocks = dict(
        re.findall(
            r"^  ([a-z-]+):\n(.*?)(?=^  [a-z-]+:\n|\Z)",
            workflow,
            re.MULTILINE | re.DOTALL,
        )
    )
    assert {"publish-pypi", "publish-pypi-stages", "github-release"} <= blocks.keys(), sorted(
        blocks
    )
    aggregate_needs = re.search(r"^    needs:\s*(.+)$", blocks["publish-pypi"], re.MULTILINE)
    assert aggregate_needs is not None, blocks["publish-pypi"]
    assert "publish-pypi-stages" in aggregate_needs.group(1), aggregate_needs.group(1)
    # The stages must still be the matrix leg, or "after the stages" would mean one of them.
    assert "matrix:" in blocks["publish-pypi-stages"]
    assert "matrix:" not in blocks["publish-pypi"]


# Written in halves so this guard is not itself the last file naming the retired document.
RETIRED_SPECIFICATION = "DAMICORE_IMPLEMENTATION" + "_SPECIFICATION"
# Either noun followed by a number, in any case, because the retired document was cited
# both ways and often without the two words adjacent -- a citation that wraps across lines
# puts arbitrary text between them. Anchoring on the number instead of on a fixed pair of
# words is what makes the guard total. No example is spelled out here: this file is scanned
# like every other, so a literal citation in this comment would match itself.
SECTION_CITATION = re.compile(r"\b(sections?|specifications?)\s+\d+(\.\d+)*\b", re.IGNORECASE)
# Published standards number their own sections, and this is a CSV project, so a line citing
# RFC 4180 or a PEP is expected prose rather than a dangling pointer. Judged per line, so an
# external citation does not excuse the rest of the file.
EXTERNAL_STANDARD = re.compile(r"\b(RFC|PEP|ISO|IEEE)\b|Apache License|License, Version")
SCANNED_SUFFIXES = {
    ".cfg",
    ".ipynb",
    ".json",
    ".md",
    ".mk",
    ".py",
    ".pyi",
    ".toml",
    ".yaml",
    ".yml",
}
# Suffixless files worth scanning. Deliberately not every suffixless file: LICENSE numbers
# its own clauses and refers to them by number, which is the licence citing itself, and
# .gitignore carries unrelated patterns.
SCANNED_NAMES = {"Makefile"}
# `.github` is the one dot-directory that holds sources; the rest are caches and virtualenvs.
SCANNED_DOT_DIRECTORY = ".github"


def test_no_repository_file_cites_the_retired_implementation_specification() -> None:
    """The implementation specification was retired, so every rule has to be stated where it
    is enforced rather than cited by section number into a document that no longer exists.

    Source comments ship inside the published wheels, which makes a dangling citation a
    user-visible defect rather than an internal one.
    """
    surfaces = [
        path
        for path in ROOT.rglob("*")
        if (path.suffix in SCANNED_SUFFIXES or path.name in SCANNED_NAMES)
        # Directories only. Applying this to the filename too would skip every dotfile,
        # including `.pre-commit-config.yaml`, which cited the retired document.
        and not any(
            part.endswith(".egg-info")
            or part in {"dist", "build", "__pycache__", ".agents"}
            or (part.startswith(".") and part != SCANNED_DOT_DIRECTORY)
            for part in path.relative_to(ROOT).parts[:-1]
        )
    ]
    # Guards the discovery. Named representatives rather than a count: one file per region
    # the scan has to reach, including the two that a filename-level dot filter and a
    # suffix-only filter each used to drop. A count would rot, since nobody raises it.
    found = {path.relative_to(ROOT).as_posix() for path in surfaces}
    for representative in (
        "Makefile",
        ".pre-commit-config.yaml",
        ".github/workflows/release.yml",
        "packages/damicore/src/damicore/api.py",
        "packages/package.mk",
        "stubs/igraph/__init__.pyi",
        "notebooks/colab_quickstart.ipynb",
        "docs/releasing.md",
    ):
        assert representative in found, representative

    citing: list[str] = []
    for path in surfaces:
        text = path.read_text(encoding="utf-8", errors="replace")
        if RETIRED_SPECIFICATION in text:
            citing.append(str(path.relative_to(ROOT)))
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if SECTION_CITATION.search(line) and not EXTERNAL_STANDARD.search(line):
                citing.append(f"{path.relative_to(ROOT)}:{number}")
    assert not citing, citing


def test_every_test_module_declares_a_registered_marker() -> None:
    """AGENTS.md requires a registered marker per suite; prose alone lets new files forget.

    The registered set is read from the root configuration rather than restated, so adding a
    marker there is the only edit needed to make it usable.

    Registered in **both** scopes a suite runs in. Pytest resolves its configuration from the
    rootdir of the invocation and inherits nothing from a parent, so a member's own
    `[tool.pytest.ini_options]` is the whole registry for `make -C packages/<name> test` --
    the command AGENTS.md sends a change to first.

    What registration buys is not selection: `-m contract` matches a mark whether or not it
    is declared. It is the ability to tell a marker from a typo. Only a registered set makes
    `pytest.mark.contarct` reportable -- as a warning, and as a collection error under
    `--strict-markers` -- so a member missing a marker cannot distinguish the two in the one
    scope where its own tests are usually run.
    """
    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pytest_options = configuration["tool"]["pytest"]["ini_options"]
    declared_markers = pytest_options["markers"]
    assert isinstance(declared_markers, list)
    registered = {
        str(entry).split(":", 1)[0].strip() for entry in cast(list[object], declared_markers)
    }

    members = sorted(
        directory
        for directory in (ROOT / "packages").iterdir()
        if (directory / "pyproject.toml").is_file()
    )
    assert len(members) >= len(PUBLIC), members
    for member in members:
        options = _tool(member / "pyproject.toml")["pytest"]
        assert isinstance(options, dict)
        member_markers = cast(dict[str, object], options)["ini_options"]
        assert isinstance(member_markers, dict)
        assert cast(dict[str, object], member_markers)["markers"] == declared_markers, member.name

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


def test_marker_registration_is_enforced_rather_than_advisory() -> None:
    """The registry above only means something if using a marker outside it fails.

    Without `--strict-markers`, `pytest.mark.contarct` marks nothing, reports a warning that
    scrolls past in a green run, and leaves the test silently unselectable by the name its
    author meant. The flag turns that into a collection error, which is what makes the
    registry a contract instead of a list. Required in every configuration a suite is run
    from, because pytest reads exactly one of them per invocation.
    """
    configurations = [ROOT / "pyproject.toml"] + [
        directory / "pyproject.toml"
        for directory in sorted((ROOT / "packages").iterdir())
        if (directory / "pyproject.toml").is_file()
    ]
    assert len(configurations) > len(PUBLIC), configurations
    for path in configurations:
        options = cast(dict[str, object], _tool(path)["pytest"])["ini_options"]
        assert isinstance(options, dict)
        addopts = str(cast(dict[str, object], options).get("addopts", ""))
        assert "--strict-markers" in addopts, path.relative_to(ROOT).as_posix()


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
    configuration = json.loads((ROOT / "pyrightconfig.json").read_text(encoding="utf-8"))
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


def test_the_repository_root_declares_the_ruff_settings_it_lints_everything_else_by() -> None:
    """The workspace's Ruff settings must reach the code that lives outside `packages/`.

    Ruff resolves its configuration per file, by walking up from that file to the nearest
    `pyproject.toml` that declares `[tool.ruff]`. The six package sections therefore govern
    `packages/<member>/**` and nothing else: with no section at the root, `tests/`,
    `benchmarks/` and `.github/scripts` fall back to Ruff's built-in defaults, so `make check`
    lints them under a rule set and a line length the repository never chose -- passing on a
    line it would reject inside a package, and never sorting their imports at all.

    Asserted equal to a member's section rather than restated here, because Ruff requires the
    section at each root it resolves and this test is what keeps those copies one rule. Which
    member is immaterial: the test above already holds all six equal to each other.
    """
    root = _tool(ROOT / "pyproject.toml")
    assert "ruff" in root, "the repository root declares no [tool.ruff]"
    member = _tool(ROOT / "packages" / "damicore" / "pyproject.toml")
    assert root["ruff"] == member["ruff"], (root["ruff"], member["ruff"])


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
    hatch: dict[str, object] = {}
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
        # The sdist exclude list is the third six-copy convention; a member that quietly
        # ships its tests or Makefile again would otherwise surface only to a user
        # unpacking the published sdist.
        hatch[member] = tool["hatch"]

    reference = members[0]
    for member in members[1:]:
        assert ruff[member] == ruff[reference], (member, ruff[member], ruff[reference])
        assert pytest_options[member] == pytest_options[reference], (
            member,
            pytest_options[member],
            pytest_options[reference],
        )
        assert hatch[member] == hatch[reference], (
            member,
            hatch[member],
            hatch[reference],
        )
