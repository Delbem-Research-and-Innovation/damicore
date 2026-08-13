"""The files object source: what a corpus is, and every way one is refused.

Objects here are the user's bytes unchanged, so the contract is not about serialization but
about which files become objects, in what order, and under what names. Each of those is a
determinism or safety property, and each has a wrong default that would fail silently.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from damicore_normalizer import (
    FileCorpusSource,
    NormalizationConfig,
    NormalizationResult,
    NormalizerError,
    materialize_objects,
)

pytestmark = pytest.mark.unit

CORPUS = NormalizationConfig(source=FileCorpusSource())


def _corpus(root: Path, files: dict[str, bytes]) -> Path:
    for name, payload in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return root


def test_a_directory_becomes_objects_without_any_split_setting(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path / "corpus", {"a.txt": b"alpha\n", "b.txt": b"beta\n"})
    result = materialize_objects(corpus, tmp_path / "out", config=CORPUS)

    assert result.object_count == 2
    assert [item.object_id for item in result.objects] == ["file_000001", "file_000002"]
    assert [item.label for item in result.objects] == ["a.txt", "b.txt"]
    assert (tmp_path / "out/objects/file_000001").read_bytes() == b"alpha\n"


def test_object_bytes_are_the_users_bytes_including_binary(tmp_path: Path) -> None:
    """NCD is defined over bytes, so a corpus must not require text. Anything that decoded,
    normalized, or re-encoded here would measure something other than the input."""
    payload = bytes(range(256)) * 4
    corpus = _corpus(tmp_path / "corpus", {"binary.bin": payload, "other.bin": payload + b"\x00"})
    result = materialize_objects(corpus, tmp_path / "out", config=CORPUS)

    assert (tmp_path / "out/objects/file_000001").read_bytes() == payload
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["object_encoding"] == "raw-bytes/1"
    assert manifest["input"]["kind"] == "files"


def test_files_sharing_a_basename_keep_distinct_labels(tmp_path: Path) -> None:
    """The distance stage requires unique labels, so a basename would fail the run one stage
    later. The relative path is unique by construction."""
    corpus = _corpus(
        tmp_path / "corpus",
        {"left/same.txt": b"one\n", "right/same.txt": b"two\n"},
    )
    result = materialize_objects(corpus, tmp_path / "out", config=CORPUS)

    labels = [item.label for item in result.objects]
    assert labels == ["left/same.txt", "right/same.txt"]
    assert len(set(labels)) == len(labels)


def test_an_explicit_file_list_is_labelled_from_the_common_ancestor(tmp_path: Path) -> None:
    corpus = _corpus(
        tmp_path / "corpus",
        {"one/a.txt": b"alpha\n", "two/b.txt": b"beta\n"},
    )
    result = materialize_objects(
        [corpus / "one/a.txt", corpus / "two/b.txt"], tmp_path / "out", config=CORPUS
    )

    assert [item.label for item in result.objects] == ["one/a.txt", "two/b.txt"]


def test_object_order_follows_the_relative_path_not_the_filesystem(tmp_path: Path) -> None:
    """Object order fixes matrix indices, so it must not depend on directory iteration order
    or on the machine's locale."""
    names = ["z.txt", "a.txt", "m/b.txt", "B.txt"]
    corpus = _corpus(tmp_path / "corpus", {name: name.encode() + b"\n" for name in names})
    result = materialize_objects(corpus, tmp_path / "out", config=CORPUS)

    assert [item.label for item in result.objects] == sorted(names)


def test_the_corpus_digest_covers_content_and_names(tmp_path: Path) -> None:
    """A corpus has no single input file, so run identity rests on this digest. It has to
    change when any file's bytes change and when the same bytes are renamed."""
    base = {"a.txt": b"alpha\n", "b.txt": b"beta\n"}
    first = materialize_objects(
        _corpus(tmp_path / "one", dict(base)), tmp_path / "out-one", config=CORPUS
    )
    same = materialize_objects(
        _corpus(tmp_path / "two", dict(base)), tmp_path / "out-two", config=CORPUS
    )
    changed = materialize_objects(
        _corpus(tmp_path / "three", {"a.txt": b"alpha\n", "b.txt": b"BETA\n"}),
        tmp_path / "out-three",
        config=CORPUS,
    )
    renamed = materialize_objects(
        _corpus(tmp_path / "four", {"a.txt": b"alpha\n", "c.txt": b"beta\n"}),
        tmp_path / "out-four",
        config=CORPUS,
    )

    def digest(result: NormalizationResult) -> str:
        payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        return str(payload["input"]["sha256"])

    assert digest(first) == digest(same)
    assert digest(first) != digest(changed)
    assert digest(first) != digest(renamed)


def test_recursion_and_hidden_files_follow_the_declared_policy(tmp_path: Path) -> None:
    corpus = _corpus(
        tmp_path / "corpus",
        {
            "top.txt": b"top\n",
            "second.txt": b"second\n",
            "nested/deep.txt": b"deep\n",
            ".hidden.txt": b"hidden\n",
        },
    )
    flat = materialize_objects(
        corpus,
        tmp_path / "flat",
        config=NormalizationConfig(source=FileCorpusSource(recursive=False)),
    )
    assert [item.label for item in flat.objects] == ["second.txt", "top.txt"]

    hidden = materialize_objects(
        corpus,
        tmp_path / "hidden",
        config=NormalizationConfig(source=FileCorpusSource(include_hidden=True)),
    )
    assert ".hidden.txt" in [item.label for item in hidden.objects]

    manifest = json.loads(flat.manifest_path.read_text(encoding="utf-8"))
    assert manifest["input"]["recursive"] is False
    assert manifest["input"]["include_hidden"] is False


def test_measuring_a_corpus_without_writing_agrees_with_materializing_it(tmp_path: Path) -> None:
    """Preflight calls this traversal with no destination; a run calls the same one with one.

    The projection a caller is asked to approve is only worth anything if it is the run's own
    arithmetic, so what is asserted is agreement -- identifiers, labels, sizes and digests --
    rather than the measurement in isolation. Exercised here rather than only through the
    orchestrator's preflight, because this is the package a change to it is validated in.
    """
    import damicore_normalizer.file_corpus as file_corpus

    corpus = _corpus(tmp_path / "corpus", {"a.txt": b"alpha\n" * 3, "nested/b.txt": b"beta\n" * 5})

    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    measured = file_corpus.scan_corpus((corpus,), FileCorpusSource())
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == before

    written = materialize_objects(corpus, tmp_path / "out", config=CORPUS)
    assert [item.model_dump() for item in measured.objects] == [
        item.model_dump() for item in written.objects
    ]
    assert measured.total_bytes == written.total_bytes


def _one_file(root: Path) -> Path:
    return _corpus(root, {"only.txt": b"one\n"})


def _with_an_empty_file(root: Path) -> Path:
    return _corpus(root, {"a.txt": b"alpha\n", "empty.txt": b""})


def _absent(root: Path) -> Path:
    return root / "absent"


def _empty_directory(root: Path) -> Path:
    return root


# Each row is one way a corpus can be unusable, with the stable public code and the message
# fragment that separates it from the other refusals sharing that code. None of these may be
# skipped silently: a dropped file changes which objects were compared without saying so.
@pytest.mark.parametrize(
    ("build", "code", "discriminator"),
    [
        pytest.param(
            _one_file, "corpus_validation_error", "at least two files", id="fewer-than-two-files"
        ),
        pytest.param(_with_an_empty_file, "corpus_validation_error", "is empty", id="empty-file"),
        pytest.param(_absent, "input_validation_error", "does not exist", id="missing-path"),
        pytest.param(_empty_directory, "corpus_validation_error", "found 0", id="empty-directory"),
    ],
)
def test_an_unusable_corpus_is_refused_with_a_stable_code(
    tmp_path: Path,
    build: Callable[[Path], Path],
    code: str,
    discriminator: str,
) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    corpus = build(root)
    with pytest.raises(NormalizerError, match=discriminator) as raised:
        materialize_objects(corpus, tmp_path / "out", config=CORPUS)
    assert raised.value.code == code


def test_a_symlinked_entry_is_refused_rather_than_followed(tmp_path: Path) -> None:
    """The distance stage rejects a symlinked object, so following one here would only move
    the failure later. Refusing keeps the run directory self-contained."""
    corpus = _corpus(tmp_path / "corpus", {"a.txt": b"alpha\n", "b.txt": b"beta\n"})
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside\n")
    (corpus / "link.txt").symlink_to(outside)

    with pytest.raises(NormalizerError, match="symlink") as raised:
        materialize_objects(corpus, tmp_path / "out", config=CORPUS)
    assert raised.value.code == "corpus_validation_error"


def test_a_symlinked_source_directory_is_followed_to_what_it_points_at(tmp_path: Path) -> None:
    """The symlink rule governs corpus entries, not the path the user names. A source path is
    resolved before the corpus is read, so naming a linked directory adopts the files behind
    it -- refusing that would reject an ordinary way of referring to a dataset while the bytes
    are copied into the run directory either way. Pinned here because a guard against it would
    be unreachable code that reads as protection."""
    corpus = _corpus(tmp_path / "corpus", {"a.txt": b"alpha\n", "b.txt": b"beta\n"})
    link = tmp_path / "link"
    link.symlink_to(corpus, target_is_directory=True)

    result = materialize_objects(link, tmp_path / "out", config=CORPUS)

    assert [item.label for item in result.objects] == ["a.txt", "b.txt"]
    assert (tmp_path / "out/objects/file_000001").read_bytes() == b"alpha\n"


def test_a_non_regular_entry_is_refused(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path / "corpus", {"a.txt": b"alpha\n", "b.txt": b"beta\n"})
    os.mkfifo(corpus / "pipe")
    with pytest.raises(NormalizerError, match="not a regular file") as raised:
        materialize_objects(corpus, tmp_path / "out", config=CORPUS)
    assert raised.value.code == "corpus_validation_error"


def test_the_same_file_listed_twice_is_refused(tmp_path: Path) -> None:
    """Two objects with identical bytes are legitimate; the same file twice is not, because
    the labels would collide and the corpus digest would claim a size it does not have."""
    corpus = _corpus(tmp_path / "corpus", {"a.txt": b"alpha\n", "b.txt": b"beta\n"})
    with pytest.raises(NormalizerError, match="same file twice") as raised:
        materialize_objects(
            [corpus / "a.txt", corpus / "b.txt", corpus / "a.txt"],
            tmp_path / "out",
            config=CORPUS,
        )
    assert raised.value.code == "corpus_validation_error"


def test_a_file_changed_during_materialization_is_reported_as_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every adopted file is re-stat'd after the copy. Without that, a corpus edited mid-run
    would produce a manifest describing bytes the run never read."""
    import damicore_normalizer.api as api
    from damicore_normalizer.scan import ScanResult

    corpus = _corpus(tmp_path / "corpus", {"a.txt": b"alpha\n", "b.txt": b"beta\n"})
    real_scan = api.scan_source

    def mutating_scan(
        source: str | Path | Sequence[str | Path],
        config: NormalizationConfig,
        *,
        objects_dir: Path | None = None,
    ) -> ScanResult:
        result = real_scan(source, config, objects_dir=objects_dir)
        (corpus / "a.txt").write_bytes(b"changed after the read\n")
        return result

    monkeypatch.setattr(api, "scan_source", mutating_scan)
    with pytest.raises(NormalizerError, match="changed during normalization") as raised:
        materialize_objects(corpus, tmp_path / "out", config=CORPUS)
    assert raised.value.code == "input_drift"


def test_a_corpus_file_that_cannot_be_read_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enumerating the corpus and reading its bytes are two passes, so a file can be gone by the
    time the second one wants it. That has to surface as the typed input failure naming the
    file, not as a bare OSError from the middle of the copy.

    Provoked by removing a file between the passes rather than by revoking permission on it:
    the suite runs as root here, where a mode of 000 is not a read failure at all.
    """
    import damicore_normalizer.file_corpus as file_corpus

    corpus = _corpus(tmp_path / "corpus", {"a.txt": b"alpha\n", "b.txt": b"beta\n"})
    real_collect = file_corpus._collect

    def collect_then_remove(
        sources: Sequence[Path], source: FileCorpusSource
    ) -> tuple[Path, list[Path]]:
        root, files = real_collect(sources, source)
        files[0].unlink()
        return root, files

    monkeypatch.setattr(file_corpus, "_collect", collect_then_remove)
    with pytest.raises(NormalizerError, match="Could not read corpus file") as raised:
        materialize_objects(corpus, tmp_path / "out", config=CORPUS)
    assert raised.value.code == "input_validation_error"


def test_a_corpus_is_copied_in_so_the_run_stays_self_contained(tmp_path: Path) -> None:
    """The object must survive the source being deleted, which is what makes checkpoint
    resume, hash re-verification, and result.save work for this source at all."""
    corpus = _corpus(tmp_path / "corpus", {"a.txt": b"alpha\n", "b.txt": b"beta\n"})
    materialize_objects(corpus, tmp_path / "out", config=CORPUS)

    adopted = tmp_path / "out/objects/file_000001"
    assert not adopted.is_symlink()
    (corpus / "a.txt").unlink()
    assert adopted.read_bytes() == b"alpha\n"


def test_several_empty_directories_are_refused_as_a_corpus(tmp_path: Path) -> None:
    """Two or more sources that yield no files at all leave no file to derive the label root
    from. The refusal must still be the typed corpus error rather than an index error from
    the root computation."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    with pytest.raises(NormalizerError, match="found 0") as raised:
        materialize_objects([first, second], tmp_path / "out", config=CORPUS)
    assert raised.value.code == "corpus_validation_error"
