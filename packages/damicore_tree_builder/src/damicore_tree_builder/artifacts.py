from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from damicore_tree_builder.models import Tree
from damicore_tree_builder.newick import to_newick


def atomic_text(path: Path, text: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def write_tree_artifacts(tree: Tree, destination: Path) -> tuple[Path, Path]:
    tree_path = destination / "tree.json"
    newick_path = destination / "tree.nwk"
    atomic_text(
        tree_path,
        json.dumps(
            tree.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
    )
    atomic_text(newick_path, to_newick(tree) + "\n")
    return tree_path, newick_path
