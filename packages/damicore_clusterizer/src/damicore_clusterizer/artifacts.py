from __future__ import annotations

import csv
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _ClusterItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    cluster: int = Field(ge=0)
    object_ids: tuple[str, ...]
    labels: tuple[str, ...]


class _ClustersArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[1]
    clusters: tuple[_ClusterItem, ...]


def _stage(path: Path, payload: str, newline: str) -> str:
    """Write `payload` beside `path` and return the temporary name, unrenamed."""
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline=newline) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        os.unlink(temporary_name)
        raise
    return temporary_name


def write_cluster_artifacts(
    destination: Path,
    object_ids: tuple[str, ...],
    labels: dict[str, str],
    cluster_for: dict[str, int],
    ordered_groups: list[tuple[str, ...]],
) -> tuple[Path, Path]:
    """Publish both cluster artifacts, or neither.

    The two files describe one clustering, and the run that follows refuses a directory that
    already holds either of them. Renaming the first into place before the second exists
    would therefore let one failed write strand a membership.csv that no later run can clear
    on its own, so both are staged first and renamed only once both exist.
    """
    membership_path = destination / "membership.csv"
    clusters_path = destination / "clusters.json"

    rows = io.StringIO()
    writer = csv.writer(rows, lineterminator="\n")
    writer.writerow(["object_id", "label", "cluster"])
    for object_id in object_ids:
        writer.writerow([object_id, labels[object_id], cluster_for[object_id]])

    payload = _ClustersArtifact(
        schema_version=1,
        clusters=tuple(
            _ClusterItem(
                cluster=cluster,
                object_ids=group,
                labels=tuple(labels[object_id] for object_id in group),
            )
            for cluster, group in enumerate(ordered_groups)
        ),
    )
    clusters_text = (
        json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    )

    membership_temp = _stage(membership_path, rows.getvalue(), newline="")
    try:
        clusters_temp = _stage(clusters_path, clusters_text, newline="\n")
    except BaseException:
        os.unlink(membership_temp)
        raise

    try:
        os.replace(membership_temp, membership_path)
    except BaseException:
        os.unlink(membership_temp)
        os.unlink(clusters_temp)
        raise
    try:
        os.replace(clusters_temp, clusters_path)
    except BaseException:
        # membership.csv is already published; withdraw it so the directory is left as found.
        os.unlink(clusters_temp)
        membership_path.unlink(missing_ok=True)
        raise
    return membership_path, clusters_path
