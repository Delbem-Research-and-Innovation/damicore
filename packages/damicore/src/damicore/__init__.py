from damicore_distance import DistanceMatrixView

from damicore.api import VERSION, estimate, load_result, run
from damicore.config import ExecutionConfig, ResourceLimits
from damicore.errors import (
    ArtifactValidationError,
    CheckpointMismatchError,
    ClusterizationError,
    CompressionError,
    ConfigurationError,
    CSVFormatError,
    DamicoreError,
    DistanceComputationError,
    DistanceMatrixValidationError,
    InputValidationError,
    MaterializationError,
    NormalizationError,
    OutputDirectoryConflictError,
    ResourceLimitError,
    TreeBuildError,
    TreeFormatError,
)
from damicore.estimate import ResourceEstimate
from damicore.result import ArtifactPaths, DamicoreResult, RunReport

# The attribute a consumer looks for. Not in __all__: it is metadata about the package,
# not part of the closed public API surface.
__version__ = VERSION

__all__ = [
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
]
