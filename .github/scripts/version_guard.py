"""Assert that a version agrees with every public package and the changelog.

One definition for the two workflows that gate on it: release.yml's tag-guard checks the
version a tag names before the expensive chain runs, and auto-tag.yml checks the version
main declares before creating that tag at all. Failing here is cheap; failing later costs
the benchmark, or worse, leaves a tag pointing at sources that disagree with it.
"""

from __future__ import annotations

import sys

import tomllib


def main() -> int:
    expected = sys.argv[1]
    packages = sys.argv[2:]
    mismatches: list[str] = []
    for package in packages:
        path = f"packages/{package}/pyproject.toml"
        with open(path, "rb") as handle:
            version = tomllib.load(handle)["project"]["version"]
        if version != expected:
            mismatches.append(
                f"{path}: version {version} != expected version {expected}"
            )
    # The same cheap-mistake class as a version mismatch: the build job's changelog
    # extraction requires this exact heading, and discovering its absence there costs
    # the whole benchmark first.
    with open("CHANGELOG.md", encoding="utf-8") as handle:
        if f"## {expected}\n" not in handle.read():
            mismatches.append(
                f"CHANGELOG.md: no '## {expected}' section for this version"
            )
    if mismatches:
        print("\n".join(mismatches), file=sys.stderr)
        return 1
    print(f"all {len(packages)} package versions and the changelog agree on {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
