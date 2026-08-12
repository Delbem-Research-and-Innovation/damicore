"""End-to-end pipeline behavior from a CSV path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from damicore import ExecutionConfig, load_result, run
from synthetic_data import generate_csv

pytestmark = pytest.mark.e2e

SERIAL = ExecutionConfig(workers=1)


def _dataset(directory: Path) -> Path:
    return generate_csv(
        directory / "dataset.csv", rows=24, columns=8, clusters=2, seed=42
    )


@pytest.mark.parametrize("split", ["columns", "rows"])
def test_pipeline_produces_complete_result_for_split(
    tmp_path: Path, split: str
) -> None:
    source = _dataset(tmp_path)
    result = run(
        source,
        split=split,
        output_dir=tmp_path / "run",
        progress=False,
        execution=SERIAL,
    )
    try:
        assert result.report.status == "completed"
        assert list(result.membership.columns) == ["object_id", "label", "cluster"]
        assert result.membership["cluster"].dtype == "int64"
        expected_objects = 8 if split == "columns" else 24
        assert len(result.membership) == expected_objects
        assert result.distance_matrix.shape == (expected_objects, expected_objects)
        assert result.tree_newick.endswith(";")
        assert result.clusters
        assert sorted(result.clusters) == list(range(len(result.clusters)))

        # The fixture is built with two groups, so recovering them is what makes this an
        # end-to-end test of DAMICORE rather than of its plumbing. The assertion is purity,
        # not an exact count: the automatic modularity cut may split a true group into
        # several communities, which loses no information, but it must never merge objects
        # from different groups. Object ids are positional and one-based.
        def group_of(object_id: str) -> int:
            return (int(object_id.split("_")[1]) - 1) % 2

        recovered = {
            frozenset(map(group_of, members)) for members in result.clusters.values()
        }
        assert recovered == {frozenset({0}), frozenset({1})}
    finally:
        result.close()


def test_completed_run_reloads_identically(tmp_path: Path) -> None:
    source = _dataset(tmp_path)
    first = run(source, output_dir=tmp_path / "run", progress=False, execution=SERIAL)
    reloaded = load_result(tmp_path / "run")
    try:
        assert reloaded.report.status == "completed"
        assert first.membership.equals(reloaded.membership)
        assert first.clusters == reloaded.clusters
        assert first.tree_newick == reloaded.tree_newick
    finally:
        first.close()
        reloaded.close()


def test_completed_run_is_reused_without_recompute(tmp_path: Path) -> None:
    source = _dataset(tmp_path)
    first = run(source, output_dir=tmp_path / "run", progress=False, execution=SERIAL)
    completed_at = (tmp_path / "run" / "manifest.json").stat().st_mtime_ns
    first.close()
    second = run(source, output_dir=tmp_path / "run", progress=False, execution=SERIAL)
    try:
        assert second.report.status == "completed"
        assert (tmp_path / "run" / "manifest.json").stat().st_mtime_ns == completed_at
    finally:
        second.close()


def test_save_copies_completed_artifacts_to_empty_destination(tmp_path: Path) -> None:
    source = _dataset(tmp_path)
    result = run(source, output_dir=tmp_path / "run", progress=False, execution=SERIAL)
    try:
        saved = result.save(tmp_path / "exported")
        loaded = load_result(saved.run_dir)
        try:
            assert loaded.report.status == "completed"
            assert result.membership.equals(loaded.membership)
        finally:
            loaded.close()
    finally:
        result.close()


# Every test above pins workers=1, which is the one execution path a user does not take by
# default. These three cover the default instead.
def _script(tmp_path: Path, source: Path, *, guarded: bool) -> Path:
    call = (
        f"result = run({str(source)!r}, output_dir={str(tmp_path / 'run')!r}, progress=False)\n"
        "result.close()\n"
        "print('completed')\n"
    )
    if guarded:
        indented = "".join(f"    {line}\n" for line in call.splitlines())
        body = f'if __name__ == "__main__":\n{indented}'
    else:
        body = call
    script = tmp_path / ("guarded.py" if guarded else "unguarded.py")
    script.write_text(f"from damicore import run\n\n{body}", encoding="utf-8")
    return script


def _run_script(script: Path) -> subprocess.CompletedProcess[str]:
    # check=False: a non-zero exit is the subject of these assertions, and the messages below
    # report the child's stderr, which CalledProcessError would swallow.
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def test_the_default_worker_count_completes_from_a_guarded_script(
    tmp_path: Path,
) -> None:
    """The default worker count opens a process pool, which nothing else in the suite does:
    every other test pins workers=1 and never reaches the pool at all."""
    completed = _run_script(_script(tmp_path, _dataset(tmp_path), guarded=True))
    assert completed.returncode == 0, completed.stderr[-2000:]
    assert completed.stdout.strip() == "completed"


def test_an_unguarded_module_level_call_names_the_missing_guard(tmp_path: Path) -> None:
    """A spawned worker re-imports the caller's __main__, so an unguarded module-level call
    re-enters the pipeline inside the child and multiprocessing refuses it. The pool reports
    only that a process died, so the diagnosis has to name the guard the caller is missing."""
    completed = _run_script(_script(tmp_path, _dataset(tmp_path), guarded=False))
    assert completed.returncode != 0
    assert '`if __name__ == "__main__":`' in completed.stderr
    assert "workers=1" in completed.stderr


ARTIFACTS = (
    "distance.npy",
    "labels.json",
    "tree.json",
    "tree.nwk",
    "membership.csv",
    "clusters.json",
)


def test_the_worker_count_does_not_change_any_artifact(tmp_path: Path) -> None:
    """The NCD matrix is independent of the worker count. The distance package
    covers this for its own stage; this pins it for every artifact the pipeline publishes."""
    source = _dataset(tmp_path)
    serial = run(
        source,
        output_dir=tmp_path / "serial",
        progress=False,
        execution=ExecutionConfig(workers=1),
    )
    serial.close()
    parallel = run(
        source,
        output_dir=tmp_path / "parallel",
        progress=False,
        execution=ExecutionConfig(workers=4),
    )
    parallel.close()
    for name in ARTIFACTS:
        assert (tmp_path / "serial" / name).read_bytes() == (
            tmp_path / "parallel" / name
        ).read_bytes(), name
