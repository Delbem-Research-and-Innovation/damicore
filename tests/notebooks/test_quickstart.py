import os
import subprocess
import sys
from pathlib import Path

import nbformat
import pytest
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient
from synthetic_data import generate_csv

pytestmark = pytest.mark.notebook


def test_quickstart_executes_in_installed_environment(tmp_path, monkeypatch):
    root = Path(__file__).parents[2]
    csv_path = generate_csv(
        tmp_path / "dataset.csv",
        rows=8,
        columns=3,
        clusters=2,
        seed=9,
    )
    monkeypatch.setenv("DAMICORE_NOTEBOOK_CSV", str(csv_path))
    monkeypatch.chdir(tmp_path)
    notebook = nbformat.read(root / "notebooks/colab_quickstart.ipynb", as_version=4)
    notebook.cells = [
        cell
        for cell in notebook.cells
        if "install" not in cell.metadata.get("tags", [])
    ]
    wheel_python = os.environ.get("DAMICORE_NOTEBOOK_PYTHON")
    if wheel_python is None and "python3" in KernelSpecManager().find_kernel_specs():
        NotebookClient(notebook, timeout=120, kernel_name="python3").execute()
        return

    source = "display = lambda value: value\n" + "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "code"
    )
    subprocess.run([wheel_python or sys.executable, "-c", source], check=True)
