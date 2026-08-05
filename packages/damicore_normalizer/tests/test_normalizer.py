import hashlib
import json
from pathlib import Path
from typing import Literal

import pytest

import damicore_normalizer.api as api
import damicore_normalizer.csv_reader as csv_reader
from damicore_normalizer import NormalizationConfig, NormalizerError, normalize_csv

pytestmark = pytest.mark.unit


def _split(value: str) -> Literal["columns", "rows"]:
    """Narrow a parametrized string to the literal the config contract declares."""
    return "rows" if value == "rows" else "columns"


def _csv(tmp_path: Path) -> Path:
    path = tmp_path / "input.csv"
    path.write_text('name,note\nAna,"a,b"\nBia,""\n', encoding="utf-8")
    return path


def test_columns_are_canonical_and_chunk_independent(tmp_path: Path) -> None:
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


def test_rows_use_positional_ids_and_arrays(tmp_path: Path) -> None:
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
    pytest.param(
        "a,a\n1,2\n", "columns", "csv_format_error", "unique", id="duplicate-header-names"
    ),
    pytest.param(",b\n1,2\n", "columns", "csv_format_error", "non-empty", id="empty-header-name"),
    pytest.param("a,b\n", "columns", "csv_format_error", "enough data rows", id="no-data-rows"),
    pytest.param(
        "a\n1\n2\n", "columns", "csv_format_error", "two columns", id="one-column-columns-split"
    ),
    pytest.param(
        "a,b\n1,2\n",
        "rows",
        "csv_format_error",
        "enough data rows",
        id="one-row-rows-split",
    ),
    pytest.param(None, "columns", "input_validation_error", "regular file", id="missing-file"),
]


@pytest.mark.parametrize(("text", "split", "code", "discriminator"), INPUT_CONTRACT_VIOLATIONS)
def test_input_contract_violation_reports_its_code_and_cause(
    tmp_path: Path,
    text: str | None,
    split: str,
    code: str,
    discriminator: str,
) -> None:
    source = tmp_path / "input.csv"
    if text is not None:
        source.write_text(text, encoding="utf-8")
    with pytest.raises(NormalizerError, match=discriminator) as raised:
        normalize_csv(source, tmp_path / "out", config=NormalizationConfig(split=_split(split)))
    assert raised.value.code == code


def test_a_declared_delimiter_and_encoding_are_used_verbatim(tmp_path: Path) -> None:
    """Specification sections 10.1 and 10.3: the declared delimiter and encoding decode the
    input, and the canonical object bytes are always UTF-8 JSON regardless of that encoding."""
    source = tmp_path / "latin.csv"
    source.write_bytes("nome;cidade\nJosé;Belém\n".encode("latin-1"))
    result = normalize_csv(
        source,
        tmp_path / "out",
        config=NormalizationConfig(delimiter=";", encoding="latin-1"),
    )
    assert [item.label for item in result.objects] == ["nome", "cidade"]
    assert (tmp_path / "out/objects/column_000001.jsonl").read_bytes() == b'"Jos\xc3\xa9"\n'
    assert (tmp_path / "out/objects/column_000002.jsonl").read_bytes() == b'"Bel\xc3\xa9m"\n'


def test_cell_text_is_preserved_and_escaped_only_by_json(tmp_path: Path) -> None:
    """Specification section 10.3: an embedded newline, quote or non-ASCII character survives
    unchanged; only the JSON representation supplies escaping."""
    source = tmp_path / "quoted.csv"
    source.write_text('text,other\n"line1\nline2","say ""hi"" ☃"\n', encoding="utf-8")
    normalize_csv(source, tmp_path / "out")
    assert (tmp_path / "out/objects/column_000001.jsonl").read_bytes() == b'"line1\\nline2"\n'
    assert (
        tmp_path / "out/objects/column_000002.jsonl"
    ).read_bytes() == b'"say \\"hi\\" \xe2\x98\x83"\n'


# Each row is a byte-level defect the parser must reject rather than silently repair: a row
# whose field count disagrees with the header, and undecodable bytes in the header and in a
# later chunk, which take different code paths.
MALFORMED_INPUTS = [
    pytest.param(b"a,b\n1,2,3\n", id="every-row-wider-than-header"),
    pytest.param(b"a,b\n1,2,3,4\n", id="two-fields-wider-than-header"),
    pytest.param(b"a,b\n1,2,3\n4,5\n", id="first-row-wider-than-header"),
    pytest.param(b"a,b\n1,2\n3,4,5\n", id="later-row-wider-than-header"),
    pytest.param(b"a,b,c\n1,2\n", id="row-narrower-than-header"),
    pytest.param(b"a,b,c\n1,2,3\n4,5\n", id="later-row-narrower-than-header"),
    pytest.param(b"a,\xffb\n1,2\n", id="undecodable-header"),
    pytest.param(b"a,b\n1,2\n\xff,4\n", id="undecodable-data-row"),
]


# Every chunk size must reach the same verdict. pandas resolves a field-count mismatch
# differently depending on where the chunk boundary falls, so a rule checked only through
# pandas would accept an input at one chunk size and reject it at another.
@pytest.mark.parametrize("chunk_rows", [1, 2, 50])
@pytest.mark.parametrize("payload", MALFORMED_INPUTS)
def test_malformed_input_is_rejected_as_a_csv_format_error(
    tmp_path: Path, payload: bytes, chunk_rows: int
) -> None:
    """Specification section 10.1: a record whose field count disagrees with the header is
    malformed. Accepting one would silently drop or invent cell values, because pandas reads a
    uniform surplus of leading fields as an index and pads a short row."""
    source = tmp_path / "malformed.csv"
    source.write_bytes(payload)
    output = tmp_path / "out"
    with pytest.raises(NormalizerError) as raised:
        normalize_csv(source, output, config=NormalizationConfig(chunk_rows=chunk_rows))
    assert raised.value.code == "csv_format_error"
    assert not (output / "manifest.json").exists()
    assert not (output / "objects").exists()


def test_a_blank_line_is_a_full_width_empty_row(tmp_path: Path) -> None:
    """Specification section 10.1 sets skip_blank_lines=False, so a blank line is preserved as
    a row of empty cells rather than being rejected as a width mismatch or skipped."""
    source = tmp_path / "blank.csv"
    source.write_text("a,b\n1,2\n\n3,4\n", encoding="utf-8")
    result = normalize_csv(
        source,
        tmp_path / "out",
        config=NormalizationConfig(split="rows", chunk_rows=1),
    )
    assert result.object_count == 3
    assert (tmp_path / "out/objects/row_000002.jsonl").read_bytes() == b'["",""]\n'


def test_more_columns_than_the_open_file_limit_stay_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Specification section 10.3: the LRU pool caps open handles, so a wide CSV forces
    eviction and reopening. Every object must still contain all of its rows, in order."""
    columns = 70
    limit = 8
    header = ",".join(f"c{index:03d}" for index in range(columns))
    rows = [",".join(f"r{row}c{index:03d}" for index in range(columns)) for row in range(3)]
    source = tmp_path / "wide.csv"
    source.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")

    peak_open_streams = 0
    write = csv_reader._FilePool.write

    def counting_write(pool: csv_reader._FilePool, name: str, payload: bytes) -> None:
        nonlocal peak_open_streams
        write(pool, name, payload)
        peak_open_streams = max(peak_open_streams, len(pool._streams))

    monkeypatch.setattr(csv_reader._FilePool, "write", counting_write)
    result = normalize_csv(
        source,
        tmp_path / "out",
        config=NormalizationConfig(chunk_rows=1, max_open_files=limit),
    )

    assert peak_open_streams == limit
    assert result.object_count == columns
    for index, item in enumerate(result.objects):
        payload = (tmp_path / "out" / item.relative_path).read_bytes()
        assert payload == "".join(f'"r{row}c{index:03d}"\n' for row in range(3)).encode("utf-8")
        assert hashlib.sha256(payload).hexdigest() == item.sha256
        assert len(payload) == item.size_bytes


def test_input_drift_during_normalization_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Specification section 19: input_drift is the one specialized code in v0.1 — it guards
    against silently normalizing a CSV that changed underneath the running scan."""
    source = _csv(tmp_path)
    real_scan_csv = api.scan_csv

    def mutating_scan_csv(
        csv_path: str | Path, config: NormalizationConfig, *, objects_dir: Path
    ) -> csv_reader.ScanResult:
        result = real_scan_csv(csv_path, config, objects_dir=objects_dir)
        source.write_text('name,note\nAna,"a,b"\nBia,""\nCid,""\n', encoding="utf-8")
        return result

    monkeypatch.setattr(api, "scan_csv", mutating_scan_csv)
    with pytest.raises(NormalizerError) as raised:
        normalize_csv(source, tmp_path / "out")
    assert raised.value.code == "input_drift"


def test_a_corrupted_written_object_fails_artifact_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The post-write hash/size re-check guards against a written object silently diverging
    from what the manifest will claim — corrupt one object and confirm it is caught."""
    source = _csv(tmp_path)
    real_scan_csv = api.scan_csv

    def corrupting_scan_csv(
        csv_path: str | Path, config: NormalizationConfig, *, objects_dir: Path
    ) -> csv_reader.ScanResult:
        result = real_scan_csv(csv_path, config, objects_dir=objects_dir)
        first_object = objects_dir / result.objects[0].relative_path.removeprefix("objects/")
        first_object.write_bytes(b"corrupted\n")
        return result

    monkeypatch.setattr(api, "scan_csv", corrupting_scan_csv)
    with pytest.raises(NormalizerError) as raised:
        normalize_csv(source, tmp_path / "out")
    assert raised.value.code == "artifact_validation_error"


def test_output_must_be_empty_and_user_files_survive(tmp_path: Path) -> None:
    source = _csv(tmp_path)
    output = tmp_path / "occupied"
    output.mkdir()
    (output / "user.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(NormalizerError) as raised:
        normalize_csv(source, output)
    assert raised.value.code == "output_conflict_error"
    assert (output / "user.txt").read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize(
    ("delimiter", "encoding", "expected"),
    [
        pytest.param("::", "utf-8", ValueError, id="multi-character-delimiter"),
        pytest.param(",", "not-an-encoding", LookupError, id="unknown-encoding"),
    ],
)
def test_configuration_rejects_an_invalid_value(
    delimiter: str, encoding: str, expected: type[Exception]
) -> None:
    with pytest.raises(expected):
        NormalizationConfig(delimiter=delimiter, encoding=encoding)
