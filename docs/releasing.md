# Releasing DAMICORE

Operational guide for maintainers. The normative release rules live in
`DAMICORE_IMPLEMENTATION_SPECIFICATION.md`, section 25.4; this file records only the
facts that exist outside the repository.

## Trigger

Push a tag `vX.Y.Z` on a commit that is on `main` (the wheels bake `blob/main/...`
URLs) where `X.Y.Z` equals the version declared by all five public
`pyproject.toml` files and `CHANGELOG.md` contains a `## X.Y.Z` heading.

To bump a version: set the five `pyproject.toml` versions, add the `## X.Y.Z`
changelog section, run `uv sync --all-packages --group dev` so `uv.lock` records
the new versions (every CI job installs with `--locked` and fails on a stale
lock), and merge before tagging.

## Gate chain (`.github/workflows/release.yml`)

1. Tag/version guard: fast check that the tag agrees with the declared versions.
2. Large-input benchmark: proves the resource budget at the tag commit.
3. Check, test, build: `make check`, `make test`, one build verified against the
   tag, `twine check`, changelog section extraction.
4. TestPyPI publish via Trusted Publishing.
5. Clean-environment smoke on Python 3.11–3.14: third-party dependencies are
   installed from PyPI using the built artifacts, then the five DAMICORE
   distributions are swapped for their pinned TestPyPI publications; the CLI and
   pipeline smoke run against that environment (notebook on 3.12 only).
6. PyPI publish via Trusted Publishing, same artifacts as step 4.
7. GitHub Release with the version's changelog section and `SHA256SUMS`.

## External preconditions (configure before the first tag)

Trusted Publishing "pending publisher" entries on both indexes, one per project
name, all with owner `Delbem-Research-and-Innovation`, repository `damicore`,
workflow `release.yml`, environment `release` — 10 entries in total:

| Index | Project |
|---|---|
| pypi.org | damicore |
| pypi.org | damicore-normalizer |
| pypi.org | damicore-distance |
| pypi.org | damicore-tree-builder |
| pypi.org | damicore-clusterizer |
| test.pypi.org | damicore |
| test.pypi.org | damicore-normalizer |
| test.pypi.org | damicore-distance |
| test.pypi.org | damicore-tree-builder |
| test.pypi.org | damicore-clusterizer |

Additionally:

- Create the GitHub environment named `release`; add required reviewers to it for
  a manual approval gate if desired.
- The organization's actions policy must allow the pinned third-party actions:
  `pypa/gh-action-pypi-publish`, `softprops/action-gh-release`, `astral-sh/setup-uv`.
- The repository must be public, or the metadata URLs baked into the wheels 404.
- Runners need roughly 5 GiB of free disk for the large benchmark.

## After a failed run

- Re-running the workflow is safe: `skip-existing` makes uploads of files already
  on TestPyPI (or PyPI) a no-op instead of a failure. The corollary: an index
  never replaces a file it already holds, so after the first TestPyPI publish of
  a version, its bytes there are frozen even if a re-tag rebuilt them; compare
  the TestPyPI downloads against the run's `SHA256SUMS` when in doubt.
- Artifacts are never rebuilt between TestPyPI and PyPI; both publish jobs upload
  the exact files the build job produced.
- A version that reached PyPI cannot be retracted; fix forward with a new patch tag.
