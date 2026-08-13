"""Verify built distributions before they are smoke-tested or published.

Enforces the distribution contract against the artifacts that will actually be uploaded,
rather than against the sources they came from:

- the distribution directory holds exactly one wheel and one sdist per allowlisted
  package and nothing else, so a private or stale artifact cannot reach an index;
- each archive's filename agrees with the name and version in its own metadata;
- no ``Requires-Dist`` entry carries a direct reference or local path, so a workspace
  path cannot leak into a published dependency;
- every distribution declares the same lockstep version, optionally equal to a release
  tag;
- every wheel that advertises ``Typing :: Typed`` actually carries the ``py.typed`` marker
  that makes the claim true, and carries its licence text;
- rebuilding yields byte-identical archive members, ignoring the ZIP container metadata
  that no build backend can hold stable.

Every check runs before the exit status is decided, so one invocation reports every
violation instead of only the first.
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
from collections.abc import Iterator
from email import message_from_bytes
from email.message import Message
from pathlib import Path
from zipfile import ZipFile

# A published requirement must be a plain PEP 508 specifier. "@" introduces a direct
# reference and the URL markers appear in any path or index pin, which is how a workspace
# source leaks into a wheel.
FORBIDDEN_IN_REQUIREMENT = ("@", "file:", "://")

# Metadata carries the distribution name unnormalized; archive filenames carry it with
# every separator run collapsed to an underscore.
_SEPARATOR_RUN = re.compile(r"[-_.]+")


def normalize(name: str) -> str:
    """Return the PEP 503 comparison form of a distribution name."""
    return _SEPARATOR_RUN.sub("-", name).lower()


def wheel_metadata(path: Path) -> Message:
    """Return the parsed ``METADATA`` of a wheel."""
    with ZipFile(path) as archive:
        names = [
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/METADATA") and name.count("/") == 1
        ]
        if len(names) != 1:
            raise ValueError(f"{path.name}: expected one .dist-info/METADATA, got {names}")
        return message_from_bytes(archive.read(names[0]))


def sdist_metadata(path: Path) -> Message:
    """Return the parsed ``PKG-INFO`` of an sdist."""
    with tarfile.open(path) as archive:
        names = [
            name
            for name in archive.getnames()
            if name.endswith("/PKG-INFO") and name.count("/") == 1
        ]
        if len(names) != 1:
            raise ValueError(f"{path.name}: expected one top-level PKG-INFO, got {names}")
        member = archive.extractfile(names[0])
        if member is None:
            raise ValueError(f"{path.name}: PKG-INFO is not a regular file")
        return message_from_bytes(member.read())


def wheel_members(path: Path) -> dict[str, bytes]:
    """Return the logical content of a wheel: member name to member bytes.

    ZIP timestamps, compression choices and entry order are deliberately excluded; they
    are container metadata that a reproducible build cannot be held to.
    """
    with ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _requirements(metadata: Message) -> list[str]:
    return [str(value) for value in metadata.get_all("Requires-Dist", [])]


def check_directory_contents(dist: Path, expected: set[str]) -> Iterator[str]:
    """Yield a failure for every missing, duplicated or unexpected artifact."""
    files = sorted(path for path in dist.iterdir() if path.is_file())
    for suffix, kind in ((".whl", "wheel"), (".tar.gz", "sdist")):
        found: dict[str, list[str]] = {}
        for path in files:
            if path.name.endswith(suffix):
                found.setdefault(normalize(path.name.split("-")[0]), []).append(path.name)
        for package in sorted(expected - found.keys()):
            yield f"missing {kind} for {package}"
        for package in sorted(found.keys() - expected):
            yield f"unexpected {kind} for {package}: {found[package]}"
        for package, names in sorted(found.items()):
            if len(names) > 1:
                yield f"more than one {kind} for {package}: {names}"

    # Dot-prefixed entries are build-tool bookkeeping (uv writes dist/.gitignore) and are
    # never uploaded. Anything else in here would be an artifact nobody accounted for.
    unclassified = [
        path.name
        for path in files
        if not path.name.endswith((".whl", ".tar.gz")) and not path.name.startswith(".")
    ]
    if unclassified:
        yield f"unexpected files in {dist}: {sorted(unclassified)}"


def check_distribution(path: Path, metadata: Message) -> Iterator[str]:
    """Yield a failure for every metadata violation in a single distribution."""
    name = metadata.get("Name")
    version = metadata.get("Version")
    if not name or not version:
        yield f"{path.name}: metadata declares no Name or Version"
        return

    stem = path.name[: -len(".whl")] if path.name.endswith(".whl") else path.name[: -len(".tar.gz")]
    filename_name, _, remainder = stem.partition("-")
    filename_version = remainder.split("-")[0]
    if normalize(filename_name) != normalize(name):
        yield f"{path.name}: filename name disagrees with metadata Name {name!r}"
    if filename_version != version:
        yield f"{path.name}: filename version disagrees with metadata Version {version!r}"

    for requirement in _requirements(metadata):
        marker = next((m for m in FORBIDDEN_IN_REQUIREMENT if m in requirement), None)
        if marker is not None:
            yield f"{path.name}: Requires-Dist {requirement!r} contains {marker!r}"


def check_wheel_advertises_only_what_it_ships(path: Path, metadata: Message) -> Iterator[str]:
    """Yield a failure when a wheel's metadata claims something its members do not deliver.

    ``Typing :: Typed`` and ``License-Expression`` are claims PyPI renders and type checkers
    act on, and both are frozen the moment a version is uploaded. The source tree is checked
    separately; this checks the archive, because only a build backend decides what a wheel
    finally contains.
    """
    with ZipFile(path) as archive:
        members = archive.namelist()
    # Importable top-level packages only. A wheel may also carry a ``<name>-<version>.data``
    # tree for scripts and data files, which is not a package and has no py.typed to ship.
    packages = {
        name.split("/")[0]
        for name in members
        if "/" in name and not name.split("/")[0].endswith((".dist-info", ".data"))
    }
    if "Typing :: Typed" in metadata.get_all("Classifier", []):
        for package in sorted(packages):
            if f"{package}/py.typed" not in members:
                yield f"{path.name}: declares Typing :: Typed but ships no {package}/py.typed"
    if not metadata.get("License-Expression"):
        yield f"{path.name}: metadata carries no License-Expression"
    if not any(
        name.startswith(f"{path.name.split('-')[0]}") and "/licenses/" in name for name in members
    ):
        yield f"{path.name}: ships no licence file in .dist-info/licenses/"


def check_lockstep_version(versions: dict[str, str], expected: str | None) -> Iterator[str]:
    """Yield a failure when the distributions disagree on a version or miss the tag."""
    distinct = sorted(set(versions.values()))
    if len(distinct) > 1:
        yield f"distributions are not in lockstep: {versions}"
    if expected is not None:
        mismatched = {
            artifact: version for artifact, version in versions.items() if version != expected
        }
        if mismatched:
            yield f"expected version {expected!r}, got {mismatched}"


def check_rebuild_is_identical(dist: Path, rebuilt: Path) -> Iterator[str]:
    """Yield a failure for every wheel whose logical content changed on rebuild."""
    for original in sorted(dist.glob("*.whl")):
        candidate = rebuilt / original.name
        if not candidate.is_file():
            yield f"{original.name}: rebuild produced no matching wheel in {rebuilt}"
            continue
        before, after = wheel_members(original), wheel_members(candidate)
        differing = sorted(
            name for name in before.keys() | after.keys() if before.get(name) != after.get(name)
        )
        if differing:
            yield f"{original.name}: rebuild changed {differing}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dist", type=Path, required=True, help="directory holding the distributions"
    )
    parser.add_argument(
        "--expect-version",
        help="version every distribution must declare, normally a release tag",
    )
    parser.add_argument(
        "--rebuilt",
        type=Path,
        help="directory holding an independent rebuild to compare wheels against",
    )
    parser.add_argument(
        "packages",
        nargs="+",
        help="the publish allowlist, as printed by `make print-public-packages`",
    )
    arguments = parser.parse_args()

    if not arguments.dist.is_dir():
        print(f"{arguments.dist} is not a directory", file=sys.stderr)
        return 1

    expected = {normalize(package) for package in arguments.packages}
    failures = list(check_directory_contents(arguments.dist, expected))

    versions: dict[str, str] = {}
    for path in sorted(arguments.dist.iterdir()):
        if path.name.endswith(".whl"):
            metadata = wheel_metadata(path)
            failures.extend(check_wheel_advertises_only_what_it_ships(path, metadata))
        elif path.name.endswith(".tar.gz"):
            metadata = sdist_metadata(path)
        else:
            continue
        failures.extend(check_distribution(path, metadata))
        version = metadata.get("Version")
        if version:
            versions[path.name] = version

    failures.extend(check_lockstep_version(versions, arguments.expect_version))
    if arguments.rebuilt is not None:
        failures.extend(check_rebuild_is_identical(arguments.dist, arguments.rebuilt))

    for failure in failures:
        print(f"verify-dist: {failure}", file=sys.stderr)
    if failures:
        return 1

    declared = ", ".join(sorted(set(versions.values()))) or "none"
    print(
        f"verify-dist: {len(expected)} packages, {len(versions)} distributions, version {declared}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
