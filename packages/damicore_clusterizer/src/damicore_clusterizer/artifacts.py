from __future__ import annotations

import csv
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


def _atomic_text(path: Path, payload: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def write_cluster_artifacts(
    destination: Path,
    object_ids: tuple[str, ...],
    labels: dict[str, str],
    cluster_for: dict[str, int],
    ordered_groups: list[tuple[str, ...]],
) -> tuple[Path, Path]:
    membership_path = destination / "membership.csv"
    descriptor, temporary_name = tempfile.mkstemp(dir=destination, prefix=".membership.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["object_id", "label", "cluster"])
            for object_id in object_ids:
                writer.writerow([object_id, labels[object_id], cluster_for[object_id]])
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, membership_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)

    clusters_path = destination / "clusters.json"
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
    _atomic_text(
        clusters_path,
        json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True, allow_nan=False)
        + "\n",
    )
    return membership_path, clusters_path
