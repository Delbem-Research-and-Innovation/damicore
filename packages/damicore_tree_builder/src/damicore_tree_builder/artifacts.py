from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from damicore_tree_builder.models import Tree
from damicore_tree_builder.newick import to_newick


def _stage(path: Path, payload: str) -> str:
    """Write `payload` beside `path` and return the temporary name, unrenamed."""
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        os.unlink(temporary_name)
        raise
    return temporary_name


def write_tree_artifacts(tree: Tree, destination: Path) -> tuple[Path, Path]:
    """Publish both tree artifacts, or neither.

    The two files describe one tree, and the run that follows refuses a directory that already
    holds either of them. Renaming the first into place before the second exists would
    therefore let one failed write strand a tree.json that no later run can clear on its own,
    so both payloads are rendered and staged first and renamed only once both exist.
    """
    tree_path = destination / "tree.json"
    newick_path = destination / "tree.nwk"

    tree_text = (
        json.dumps(
            tree.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )
    newick_text = to_newick(tree) + "\n"

    tree_temp = _stage(tree_path, tree_text)
    try:
        newick_temp = _stage(newick_path, newick_text)
    except BaseException:
        os.unlink(tree_temp)
        raise

    try:
        os.replace(tree_temp, tree_path)
    except BaseException:
        os.unlink(tree_temp)
        os.unlink(newick_temp)
        raise
    try:
        os.replace(newick_temp, newick_path)
    except BaseException:
        # tree.json is already published; withdraw it so the directory is left as found.
        os.unlink(newick_temp)
        tree_path.unlink(missing_ok=True)
        raise
    return tree_path, newick_path
