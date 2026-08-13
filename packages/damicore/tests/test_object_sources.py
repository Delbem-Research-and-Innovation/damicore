"""The source axis as the orchestrator exposes it: run, estimate, run identity, and the CLI.

The stage suites prove what each source produces. What is proved here is that the choice of
source reaches every surface that depends on it -- the resource projection, the run manifest,
the configuration hash that names a run directory -- and that a setting belonging to another
source is refused instead of quietly dropped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from damicore import ConfigurationError, ExecutionConfig, estimate, run
from damicore.cli import main

pytestmark = pytest.mark.contract

SERIAL = ExecutionConfig(workers=1)


def _corpus(root: Path) -> Path:
    root.mkdir(parents=True)
    shared = b"the quick brown fox jumps over the lazy dog\n" * 12
    (root / "one.bin").write_bytes(shared)
    (root / "two.bin").write_bytes(shared + b"tail\n")
    (root / "three.bin").write_bytes(bytes(range(256)) * 6)
    (root / "four.bin").write_bytes(bytes(range(256)) * 6 + b"\x00\x01")
    return root


def _workbook(path: Path) -> Path:
    """Three columns of five rows, deliberately uneven.

    A perfectly regular grid makes several Neighbor Joining branches exactly zero, which the
    tree contract rejects; the point of the fixture is the source, not a degenerate tree.
    """
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["alpha", "beta", "gamma"])
    for row in range(1, 6):
        sheet.append(
            [
                "shared preamble " * row,
                f"beta value {row}" * (row + 1),
                f"unrelated {row * 7}",
            ]
        )
    workbook.save(path)
    return path


def test_a_file_corpus_runs_end_to_end_without_any_dataset_setting(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path / "corpus")
    result = run(
        corpus,
        source_kind="files",
        output_dir=tmp_path / "run",
        progress=False,
        execution=SERIAL,
    )
    try:
        assert result.report.status == "completed"
        assert result.report.object_count == 4
        assert sorted(result.membership["label"]) == [
            "four.bin",
            "one.bin",
            "three.bin",
            "two.bin",
        ]
    finally:
        result.close()

    manifest = json.loads((tmp_path / "run/manifest.json").read_text(encoding="utf-8"))
    assert manifest["input"]["kind"] == "files"
    assert manifest["config"]["source_kind"] == "files"
    # A setting that does not apply records None rather than a default that never applied.
    assert manifest["config"]["split"] is None
    assert manifest["config"]["delimiter"] is None
    assert manifest["config"]["encoding"] is None


def test_a_list_of_files_is_accepted_as_a_corpus(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path / "corpus")
    result = run(
        [corpus / "one.bin", corpus / "two.bin", corpus / "three.bin"],
        source_kind="files",
        output_dir=tmp_path / "run",
        progress=False,
        execution=SERIAL,
    )
    try:
        assert result.report.object_count == 3
    finally:
        result.close()


def test_a_binary_corpus_recovers_the_groups_its_content_implies(tmp_path: Path) -> None:
    """Objects are not required to be text. Two near-duplicate binaries must land together
    and the unrelated pair apart, or the corpus source is measuring the wrong bytes."""
    corpus = _corpus(tmp_path / "corpus")
    result = run(
        corpus,
        source_kind="files",
        output_dir=tmp_path / "run",
        progress=False,
        execution=SERIAL,
        num_clusters=2,
    )
    try:
        assignment = dict(
            zip(result.membership["label"], result.membership["cluster"], strict=True)
        )
    finally:
        result.close()
    assert assignment["one.bin"] == assignment["two.bin"]
    assert assignment["three.bin"] == assignment["four.bin"]
    assert assignment["one.bin"] != assignment["three.bin"]


def test_a_corpus_run_is_reproducible_byte_for_byte(tmp_path: Path) -> None:
    """Object order fixes matrix indices, so a corpus whose enumeration varied would produce
    a different tree from the same files."""
    corpus = _corpus(tmp_path / "corpus")
    for name in ("first", "second"):
        result = run(
            corpus,
            source_kind="files",
            output_dir=tmp_path / name,
            progress=False,
            execution=SERIAL,
        )
        result.close()
    for artifact in ("distance.npy", "labels.json", "tree.nwk", "membership.csv", "clusters.json"):
        assert (tmp_path / "first" / artifact).read_bytes() == (
            tmp_path / "second" / artifact
        ).read_bytes(), artifact


def test_a_corpus_nested_in_one_subdirectory_keeps_the_requested_root(tmp_path: Path) -> None:
    """Labels are relative to the directory that was asked for, not to wherever the files
    happen to share an ancestor.

    Preflight expands a directory into its files. Handing that expansion back to the
    materialization step re-derives the root from the files themselves, so a corpus whose
    files all sit under one subdirectory loses that path component; the set digest covers
    labels, so preflight and the run then disagree and a legitimate corpus fails outright.
    """
    corpus = tmp_path / "corpus"
    (corpus / "sub").mkdir(parents=True)
    (corpus / "sub/a.bin").write_bytes(b"alpha content here\n" * 4)
    (corpus / "sub/b.bin").write_bytes(b"beta content here\n" * 4)

    preview = estimate(corpus, source_kind="files")
    result = run(
        corpus,
        source_kind="files",
        output_dir=tmp_path / "run",
        progress=False,
        execution=SERIAL,
    )
    try:
        assert sorted(result.membership["label"]) == ["sub/a.bin", "sub/b.bin"]
    finally:
        result.close()

    manifest = json.loads((tmp_path / "run/manifest.json").read_text(encoding="utf-8"))
    assert manifest["input"]["sha256"] == preview.input_sha256


def test_a_worksheet_runs_end_to_end_and_records_its_sheet(tmp_path: Path) -> None:
    book = _workbook(tmp_path / "book.xlsx")
    result = run(
        book,
        source_kind="xlsx",
        output_dir=tmp_path / "run",
        progress=False,
        execution=SERIAL,
    )
    try:
        assert result.report.status == "completed"
        assert list(result.membership["label"]) == ["alpha", "beta", "gamma"]
    finally:
        result.close()
    manifest = json.loads((tmp_path / "run/manifest.json").read_text(encoding="utf-8"))
    assert manifest["input"]["kind"] == "xlsx"
    assert manifest["config"]["sheet"] is None
    assert manifest["config"]["split"] == "columns"


def test_estimate_reports_the_source_it_was_given(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path / "corpus")
    preview = estimate(corpus, source_kind="files")
    assert preview.source_kind == "files"
    assert preview.split is None
    assert preview.object_count == 4
    assert len(preview.source_paths) == 4
    # The corpus is copied into the run directory, so its bytes are part of what a run needs.
    assert preview.normalized_bytes == sum(path.stat().st_size for path in preview.source_paths)
    assert preview.required_free_disk_bytes > preview.normalized_bytes


# Each row is a setting that belongs to another source. Dropping one silently would let a
# caller believe it took effect while the artifacts answered a different question.
@pytest.mark.parametrize(
    ("kwargs", "discriminator"),
    [
        pytest.param({"source_kind": "files", "split": "rows"}, "split", id="split-on-files"),
        pytest.param(
            {"source_kind": "files", "delimiter": ";"}, "delimiter", id="delimiter-on-files"
        ),
        pytest.param(
            {"source_kind": "xlsx", "delimiter": ";"}, "delimiter", id="delimiter-on-xlsx"
        ),
        pytest.param(
            {"source_kind": "xlsx", "encoding": "latin-1"}, "encoding", id="encoding-on-xlsx"
        ),
        pytest.param({"source_kind": "delimited", "sheet": "S"}, "sheet", id="sheet-on-delimited"),
        pytest.param(
            {"source_kind": "delimited", "recursive": True},
            "recursive",
            id="recursive-on-delimited",
        ),
        pytest.param({"source_kind": "nonsense"}, "source_kind must be", id="unknown-source-kind"),
    ],
)
def test_a_setting_from_another_source_is_refused(
    tmp_path: Path, kwargs: dict[str, object], discriminator: str
) -> None:
    source = tmp_path / "dataset.csv"
    source.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match=discriminator):
        estimate(source, **kwargs)  # pyright: ignore[reportArgumentType]


def test_the_source_is_part_of_run_identity(tmp_path: Path) -> None:
    """Two runs over the same bytes but a different source are different runs, so the default
    output directory must not collide. A shared configuration hash would make one silently
    reuse the other's completed artifacts."""
    book = _workbook(tmp_path / "book.xlsx")
    columns = run(
        book,
        source_kind="xlsx",
        output_dir=tmp_path / "columns",
        progress=False,
        execution=SERIAL,
    )
    rows = run(
        book,
        source_kind="xlsx",
        split="rows",
        output_dir=tmp_path / "rows",
        progress=False,
        execution=SERIAL,
    )
    try:
        assert columns.report.object_count == 3
        assert rows.report.object_count == 5
    finally:
        columns.close()
        rows.close()

    first = json.loads((tmp_path / "columns/manifest.json").read_text(encoding="utf-8"))
    second = json.loads((tmp_path / "rows/manifest.json").read_text(encoding="utf-8"))
    assert first["config_hash"] != second["config_hash"]
    assert first["run_id"] != second["run_id"]


def test_the_cli_runs_a_corpus_and_a_worksheet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = _corpus(tmp_path / "corpus")
    assert (
        main(
            [
                "run",
                str(corpus),
                "--source",
                "files",
                "--workers",
                "1",
                "--no-progress",
                "--output-dir",
                str(tmp_path / "corpus-run"),
            ]
        )
        == 0
    )
    capsys.readouterr()

    book = _workbook(tmp_path / "book.xlsx")
    assert (
        main(
            [
                "estimate",
                str(book),
                "--source",
                "xlsx",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["source_kind"] == "xlsx"
    assert payload["object_count"] == 3


def test_the_cli_reports_a_rejected_setting_as_a_configuration_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = _corpus(tmp_path / "corpus")
    assert main(["estimate", str(corpus), "--source", "files", "--delimiter", ";"]) == 2
    assert json.loads(capsys.readouterr().err)["code"] == "configuration_error"
