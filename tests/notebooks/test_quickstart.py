"""Executable notebook contract.

The notebook must execute cell by cell in a kernel that resolves ``damicore`` from
installed wheels, never from the checkout. CI builds that kernel and names it in
``DAMICORE_NOTEBOOK_KERNEL``; the test refuses to substitute a weaker execution mode when
no such kernel exists, because flattening the cells into one script would stop exercising
the notebook display protocol and the per-cell failure boundaries Colab users depend on.
"""

import os
from pathlib import Path

import nbformat
import pytest
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient
from synthetic_data import generate_csv

pytestmark = pytest.mark.notebook

# Generous enough for a cold kernel on a shared runner, bounded so a hung cell fails the
# test instead of consuming the whole workflow timeout.
CELL_TIMEOUT_SECONDS = 300


def test_quickstart_executes_in_installed_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kernel = os.environ.get("DAMICORE_NOTEBOOK_KERNEL", "python3")
    if kernel not in KernelSpecManager().find_kernel_specs():
        pytest.skip(
            f"kernel {kernel!r} is not registered; run the notebook lane, which installs "
            "the built wheels into a clean environment and registers a kernel for it"
        )

    root = Path(__file__).parents[2]
    csv_path = generate_csv(
        tmp_path / "dataset.csv",
        rows=8,
        columns=3,
        clusters=2,
        seed=9,
    )
    monkeypatch.setenv("DAMICORE_NOTEBOOK_CSV", str(csv_path))
    # The kernel inherits this working directory, so the notebook cannot reach the checkout.
    monkeypatch.chdir(tmp_path)

    # nbformat ships no py.typed, so its node objects are untyped; the ignores below are
    # confined to the calls that cross that boundary.
    notebook = nbformat.read(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        root / "notebooks/colab_quickstart.ipynb", as_version=4
    )
    notebook.cells = [  # pyright: ignore[reportUnknownMemberType]
        cell
        for cell in notebook.cells  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if "install" not in cell.metadata.get("tags", [])  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    ]
    NotebookClient(
        notebook,  # pyright: ignore[reportUnknownArgumentType]
        timeout=CELL_TIMEOUT_SECONDS,
        kernel_name=kernel,
    ).execute()
