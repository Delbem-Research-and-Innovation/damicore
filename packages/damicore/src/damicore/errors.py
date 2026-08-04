from __future__ import annotations

import re


def _default_code(name: str) -> str:
    words = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", words).lower()


class DamicoreError(Exception):
    def __init__(self, message: str, *, code: str | None = None, **context: object) -> None:
        super().__init__(message)
        self.code = code or _default_code(type(self).__name__)
        self.context = context


class ConfigurationError(DamicoreError):
    pass


class InputValidationError(DamicoreError):
    pass


class CSVFormatError(InputValidationError):
    pass


class ResourceLimitError(DamicoreError):
    pass


class OutputDirectoryConflictError(DamicoreError):
    pass


class CheckpointMismatchError(DamicoreError):
    pass


class NormalizationError(DamicoreError):
    pass


class CompressionError(DamicoreError):
    pass


class DistanceComputationError(DamicoreError):
    pass


class DistanceMatrixValidationError(DamicoreError):
    pass


class TreeBuildError(DamicoreError):
    pass


class TreeFormatError(TreeBuildError):
    pass


class ClusterizationError(DamicoreError):
    pass


class ArtifactValidationError(DamicoreError):
    pass


class MaterializationError(DamicoreError):
    pass
