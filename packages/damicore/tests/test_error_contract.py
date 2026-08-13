"""The public failure contract, which this module is the source of truth for.

One rule holds for every public exception: ``code`` is the class name in snake_case, and
``input_drift`` is the version 0.2 exception to it. That rule is what callers and the CLI's
JSON error envelope depend on, so it is asserted here as a rule over the whole hierarchy
rather than as a per-class expectation. A class added to the hierarchy, or a stage code
added to the translation table, is covered the moment it exists.

Messages are deliberately not asserted here. They must be actionable, which makes them a
human-facing surface that may be reworded; the per-stage suites match them only where they
are the sole way to tell two violations of the same contract apart.
"""

import pytest
from damicore_clusterizer import ClusterizerError
from damicore_distance import DistanceError
from damicore_normalizer import NormalizerError
from damicore_tree_builder import TreeBuilderError

from damicore import errors as error_module
from damicore.api import _PRESERVED_CODES, _STAGE_TRANSLATIONS, _translated_stage_error
from damicore.errors import DamicoreError, _default_code

pytestmark = pytest.mark.unit

STAGE_BASES = {
    NormalizerError: "normalizer_error",
    DistanceError: "distance_error",
    TreeBuilderError: "tree_builder_error",
    ClusterizerError: "clusterizer_error",
}


def _public_error_classes() -> list[type[DamicoreError]]:
    """Every public failure class, discovered rather than listed."""
    return sorted(
        (
            value
            for value in vars(error_module).values()
            if isinstance(value, type)
            and issubclass(value, DamicoreError)
            and value.__module__ == error_module.__name__
        ),
        key=lambda cls: cls.__name__,
    )


def test_every_public_error_derives_its_code_from_its_class_name() -> None:
    classes = _public_error_classes()
    # Guards the discovery itself: an empty or truncated scan would pass every assertion.
    assert len(classes) >= 16, [cls.__name__ for cls in classes]
    for cls in classes:
        assert cls("boom").code == _default_code(cls.__name__), cls.__name__


def test_default_code_conversion_handles_acronyms_and_suffixes() -> None:
    assert _default_code("NCDFormatError") == "ncd_format_error"
    assert _default_code("DatasetFormatError") == "dataset_format_error"
    assert _default_code("OutputDirectoryConflictError") == "output_directory_conflict_error"


def test_translation_reports_the_raised_class_never_the_stage_vocabulary() -> None:
    """A stage's internal code must not survive into the public envelope."""
    for base, by_code, fallback in _STAGE_TRANSLATIONS:
        for code, expected in [*by_code.items(), ("an_unmapped_stage_code", fallback)]:
            translated = _translated_stage_error(base("boom", code=code), stage="normalize")
            assert isinstance(translated, expected), (base.__name__, code)
            if code in _PRESERVED_CODES:
                assert translated.code == code, (base.__name__, code)
            else:
                assert translated.code == _default_code(type(translated).__name__), (
                    base.__name__,
                    code,
                )


def test_translation_of_a_stage_default_code_reports_the_public_class() -> None:
    """The stage bases default to their own code; translation must not leak it."""
    for base, default_code in STAGE_BASES.items():
        error = base("boom")
        assert error.code == default_code
        translated = _translated_stage_error(error)
        assert translated.code == _default_code(type(translated).__name__), base.__name__
        assert translated.code != default_code, base.__name__


def test_input_drift_is_the_only_code_that_survives_translation() -> None:
    """Exactly one specialized code is sanctioned in 0.2."""
    assert _PRESERVED_CODES == frozenset({"input_drift"})
    translated = _translated_stage_error(NormalizerError("boom", code="input_drift"))
    assert translated.code == "input_drift"


def test_an_unknown_stage_failure_becomes_the_base_public_error() -> None:
    translated = _translated_stage_error(RuntimeError("boom"), stage="cluster")
    assert type(translated) is DamicoreError
    assert translated.code == "damicore_error"
    assert translated.context["stage"] == "cluster"


def test_translation_preserves_the_message_and_records_the_stage() -> None:
    translated = _translated_stage_error(
        NormalizerError("CSV header names must be unique", code="dataset_format_error"),
        stage="normalize",
    )
    assert str(translated) == "CSV header names must be unique"
    assert translated.context["stage"] == "normalize"
