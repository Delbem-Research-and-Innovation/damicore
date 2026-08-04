import hashlib
import json

import pytest

from damicore_normalizer import NormalizationConfig, NormalizerError, normalize_csv


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


@pytest.mark.parametrize("text", ["a,a\n1,2\n", ",b\n1,2\n", "a,b\n"])
def test_invalid_csv_contract_fails(tmp_path, text):
    source = tmp_path / "bad.csv"
    source.write_text(text, encoding="utf-8")
    with pytest.raises(NormalizerError):
        normalize_csv(source, tmp_path / "out")


def test_output_must_be_empty(tmp_path):
    source = _csv(tmp_path)
    output = tmp_path / "occupied"
    output.mkdir()
    (output / "user.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(NormalizerError):
        normalize_csv(source, output)
    assert (output / "user.txt").read_text(encoding="utf-8") == "preserve"


def test_path_and_shape_guards(tmp_path):
    with pytest.raises(NormalizerError, match="regular file"):
        normalize_csv(tmp_path / "missing.csv", tmp_path / "missing-out")
    one_column = tmp_path / "one.csv"
    one_column.write_text("a\n1\n2\n", encoding="utf-8")
    with pytest.raises(NormalizerError, match="two columns"):
        normalize_csv(one_column, tmp_path / "one-out")
    one_row = tmp_path / "row.csv"
    one_row.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(NormalizerError, match="enough"):
        normalize_csv(
            one_row,
            tmp_path / "row-out",
            config=NormalizationConfig(split="rows"),
        )


def test_configuration_validation():
    with pytest.raises(ValueError):
        NormalizationConfig(delimiter="::")
    with pytest.raises(LookupError):
        NormalizationConfig(encoding="not-an-encoding")
