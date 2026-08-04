from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TreeNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    id: str
    kind: Literal["leaf", "internal"]
    label: str | None = None


class TreeEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source: str
    target: str
    length: float = Field(allow_inf_nan=False)


class Tree(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    root_id: str
    nodes: tuple[TreeNode, ...]
    edges: tuple[TreeEdge, ...]


class TreeBuildResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    tree_path: Path
    newick_path: Path
    leaf_count: int = Field(ge=0)
    negative_branch_count: int = Field(ge=0)
    timing: float = Field(ge=0)
