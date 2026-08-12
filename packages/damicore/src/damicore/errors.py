from __future__ import annotations

import re


def _default_code(name: str) -> str:
    words = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", words).lower()


class DamicoreError(Exception):
    """Base class of every public DAMICORE failure, and the only one worth catching broadly.

    ``code`` is the stable machine-readable identifier for the failure: the class name in
    snake_case, with ``input_drift`` as the single 0.1 exception. It is what the CLI's JSON
    error envelope reports, and it never carries a stage's internal vocabulary. ``context``
    holds bounded diagnostic values supplied at the raise site; it never contains CSV cell
    contents or whole input rows.
    """

    def __init__(self, message: str, *, code: str | None = None, **context: object) -> None:
        super().__init__(message)
        self.code = code or _default_code(type(self).__name__)
        self.context = context


class ConfigurationError(DamicoreError):
    """An argument or configuration value is invalid, so no run directory was created."""


class InputValidationError(DamicoreError):
    """The input CSV is unusable: unreadable, or changed on disk mid-run (``input_drift``)."""


class CSVFormatError(InputValidationError):
    """The CSV violates the CSV contract: bad, empty, or duplicated header names, a row whose
    field count disagrees with the header, or too few columns or data rows to cluster."""


class ResourceLimitError(DamicoreError):
    """Preflight projected a run outside the configured ``ResourceLimits``.

    ``context["estimate"]`` holds the ``ResourceEstimate``, whose ``violations`` names every
    gate that failed. Reshape the split or reduce the input; individual limits may be raised
    through ``ExecutionConfig.limits`` after reviewing ``estimate()``, but the free-disk gate
    is always enforced.
    """


class OutputDirectoryConflictError(DamicoreError):
    """The output path exists and is neither empty nor a resumable run of the same input and
    configuration, or reuse or resume of a compatible one is disabled. Nothing is overwritten."""


class CheckpointMismatchError(DamicoreError):
    """Resumable state exists but cannot be trusted: a different runtime fingerprint, or a
    checkpoint that disagrees with the artifacts beside it. Start over in a fresh directory."""


class NormalizationError(DamicoreError):
    """The normalization stage failed for a reason with no more specific class."""


class CompressionError(DamicoreError):
    """The compressor rejected an object while measuring its compressed size."""


class DistanceComputationError(DamicoreError):
    """The NCD stage failed, including a worker process that died.

    A dead pool usually means a script-level call missing its ``if __name__ == "__main__":``
    guard, or a worker killed for running out of memory; ``ExecutionConfig(workers=1)``
    avoids the pool entirely.
    """


class DistanceMatrixValidationError(DamicoreError):
    """The computed NCD matrix broke an invariant: wrong shape or dtype, a non-finite value, a
    non-zero diagonal entry, or asymmetry."""


class TreeBuildError(DamicoreError):
    """The Neighbor Joining stage failed, including rejecting the distance matrix it was
    given as input."""


class TreeFormatError(TreeBuildError):
    """A tree artifact is not a valid unrooted binary tree: duplicate or dangling node ids,
    a non-internal or non-binary root, non-finite branch lengths, or a disconnected graph."""


class ClusterizationError(DamicoreError):
    """The FastGreedy stage failed, or its communities did not cover every leaf exactly once."""


class ArtifactValidationError(DamicoreError):
    """A persisted artifact failed schema validation, its recorded size or SHA-256, path
    containment inside the run directory, or the cross-artifact verification a run must pass
    before it becomes ``completed``."""


class MaterializationError(DamicoreError):
    """``DistanceMatrixView.to_pandas()`` would exceed the configured materialization limit.
    Read through ``head()`` or NumPy slicing, or pass ``force=True`` to accept the cost."""
