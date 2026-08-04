import hashlib
import json

import pytest

from damicore_normalizer import NormalizationConfig, NormalizerError, normalize_csv

pytestmark = pytest.mark.unit


def _csv(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text('name,note\nAna,"a,b"\nBia,""\n', encoding="utf-8")
    return path


def test_columns_are_canonical_and_chunk_independent(tmp_path):
    source = _csv(tmp_path)
    first = normalize_csv(
        source,
        tmp_path / "one",
        config=NormalizationConfig(chunk_rows=1),
    )
    second = normalize_csv(
        source,
        tmp_path / "two",
        config=NormalizationConfig(chunk_rows=50),
    )
    assert second.total_bytes == first.total_bytes

    expected = [b'"Ana"\n"Bia"\n', b'"a,b"\n""\n']
    assert first.object_count == 2
    for index, payload in enumerate(expected, 1):
        left = tmp_path / "one" / "objects" / f"column_{index:06d}.jsonl"
        right = tmp_path / "two" / "objects" / f"column_{index:06d}.jsonl"
        assert left.read_bytes() == right.read_bytes() == payload
        assert hashlib.sha256(payload).hexdigest() == first.objects[index - 1].sha256
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["input"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["input"]["size_bytes"] == source.stat().st_size


def test_rows_use_positional_ids_and_arrays(tmp_path):
    result = normalize_csv(
        _csv(tmp_path),
        tmp_path / "rows",
        config=NormalizationConfig(split="rows", chunk_rows=1),
    )
    assert [item.object_id for item in result.objects] == ["row_000001", "row_000002"]
    assert (tmp_path / "rows/objects/row_000001.jsonl").read_bytes() == b'["Ana","a,b"]\n'


# Each row is one way the input contract can be violated: the CSV text (None for a path that
# is not a file), the config overrides that make it a violation, the stable code from
# specification section 19, and the message fragment separating it from the other violations
# that share that code. Adding a violation is adding a row, and it fails under its own name.
INPUT_CONTRACT_VIOLATIONS = [
    pytest.param("a,a\n1,2\n", {}, "csv_format_error", "unique", id="duplicate-header-names"),
    pytest.param(",b\n1,2\n", {}, "csv_format_error", "non-empty", id="empty-header-name"),
    pytest.param("a,b\n", {}, "csv_format_error", "enough data rows", id="no-data-rows"),
    pytest.param("a\n1\n2\n", {}, "csv_format_error", "two columns", id="one-column-columns-split"),
    pytest.param(
        "a,b\n1,2\n",
        {"split": "rows"},
        "csv_format_error",
        "enough data rows",
        id="one-row-rows-split",
    ),
    pytest.param(None, {}, "input_validation_error", "regular file", id="missing-file"),
]


@pytest.mark.parametrize(("text", "overrides", "code", "discriminator"), INPUT_CONTRACT_VIOLATIONS)
def test_input_contract_violation_reports_its_code_and_cause(
    tmp_path, text, overrides, code, discriminator
):
    source = tmp_path / "input.csv"
    if text is not None:
        source.write_text(text, encoding="utf-8")
    with pytest.raises(NormalizerError, match=discriminator) as raised:
        normalize_csv(source, tmp_path / "out", config=NormalizationConfig(**overrides))
    assert raised.value.code == code


def test_output_must_be_empty_and_user_files_survive(tmp_path):
    source = _csv(tmp_path)
    output = tmp_path / "occupied"
    output.mkdir()
    (output / "user.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(NormalizerError) as raised:
        normalize_csv(source, output)
    assert raised.value.code == "output_conflict_error"
    assert (output / "user.txt").read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param({"delimiter": "::"}, ValueError, id="multi-character-delimiter"),
        pytest.param({"encoding": "not-an-encoding"}, LookupError, id="unknown-encoding"),
    ],
)
def test_configuration_rejects_an_invalid_value(overrides, expected):
    with pytest.raises(expected):
        NormalizationConfig(**overrides)
