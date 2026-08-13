from damicore_normalizer.api import materialize_objects, normalize_csv
from damicore_normalizer.config import (
    DelimitedSource,
    FileCorpusSource,
    NormalizationConfig,
    SpreadsheetSource,
)
from damicore_normalizer.errors import NormalizerError
from damicore_normalizer.manifest import (
    NormalizationManifest,
    NormalizationResult,
    ObjectDescriptor,
)

__all__ = [
    "materialize_objects",
    "normalize_csv",
    "NormalizationConfig",
    "DelimitedSource",
    "SpreadsheetSource",
    "FileCorpusSource",
    "NormalizationResult",
    # The schema of manifest.json, which is the artifact the next stage reads. Exported
    # because it is already the documented contract between stages, so a consumer validating
    # one should not have to reach past this package's public surface to do it.
    "NormalizationManifest",
    "ObjectDescriptor",
    "NormalizerError",
]
