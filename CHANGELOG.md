# Changelog

Each released version is one `## X.Y.Z` section. That heading format is a contract, not a
style: `.github/scripts/version_guard.py` refuses to tag a version whose section is missing,
and `release.yml` extracts the section verbatim as the GitHub Release body. A heading that
carries anything else, a date included, matches neither and fails the release.

## Unreleased

- Declare `numpy` in `damicore`, which imports it directly, and drop it from
  `damicore-clusterizer`, which never did. Installing `damicore-clusterizer` alone no
  longer pulls NumPy.
- Fix the stage examples on PyPI: the tree-builder and clusterizer examples now read the
  paths the previous stage actually writes, and the distance example carries the
  `if __name__ == "__main__":` guard its process pool requires.
- Correct the documented meaning of CLI exit status 4: it covers any failed stage, not
  only artifact validation.
- Document the public API. Every exported symbol now carries a docstring, and `run`,
  `estimate` and `load_result` document their parameters, returns and failure modes.

## 0.1.0

- Define the first public API for estimate, execution, loading, and results.
- Add canonical CSV normalization, exact resumable NCD, deterministic Neighbor
  Joining, and FastGreedy leaf clustering.
- Add versioned, hashed artifacts; resource gates; CLI; wheel and release gates.
