"""End-to-end pipeline behavior from a CSV path (specification sections 2, 9, 24.2)."""

from __future__ import annotations

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
