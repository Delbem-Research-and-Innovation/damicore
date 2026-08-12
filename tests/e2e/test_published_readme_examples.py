"""Every Python example on a PyPI project page runs.

Each `packages/*/README.md` is the `long_description` of a published distribution, so a
broken example there is a defect a user meets before any code of theirs runs, and one that
a version upload freezes. Three of the four stage examples were broken this way and no gate
noticed, because nothing in the repository ever executed them.

The examples are run as real subprocesses rather than `exec`ed: the distance example opens a
process pool and is therefore written under `if __name__ == "__main__":`, which only holds
for a script. They are also run in one shared directory in stage order, because the stage
READMEs tell the reader they chain -- the tree builder consumes what the distance stage
wrote. That makes the chain itself part of what this asserts.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from synthetic_data import generate_csv

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).parents[2]
PYTHON_BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)

# Stage order, then the aggregate. The four stages share one directory so that each one
# reads what the previous wrote; the aggregate is independent and gets its own.
CHAINED = [
    "damicore_normalizer",
    "damicore_distance",
    "damicore_tree_builder",
    "damicore_clusterizer",
]


def _examples(package: str) -> list[str]:
    readme = ROOT / "packages" / package / "README.md"
    blocks = PYTHON_BLOCK.findall(readme.read_text(encoding="utf-8"))
    assert blocks, f"{package}/README.md declares no Python example"
    return blocks


def _run(source: str, workdir: Path, label: str) -> None:
    script = workdir / f"{label}.py"
    script.write_text(source, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, script.name],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=300,
        # The failure is the finding, so it is asserted below with the example's own
        # stderr attached rather than raised as a bare CalledProcessError.
        check=False,
    )
    assert completed.returncode == 0, (
        f"{label} example failed with status {completed.returncode}\n"
        f"--- source ---\n{source}\n--- stderr ---\n{completed.stderr[-2000:]}"
    )


def test_stage_readme_examples_run_and_chain(tmp_path: Path) -> None:
    generate_csv(tmp_path / "dataset.csv", rows=12, columns=4, clusters=2, seed=7)
    for package in CHAINED:
        for index, source in enumerate(_examples(package)):
            _run(source, tmp_path, f"{package}_{index}")


def test_aggregate_readme_examples_run(tmp_path: Path) -> None:
    generate_csv(tmp_path / "dataset.csv", rows=12, columns=4, clusters=2, seed=7)
    for index, source in enumerate(_examples("damicore")):
        _run(source, tmp_path, f"damicore_{index}")
