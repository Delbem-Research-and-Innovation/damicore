from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ClusterResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    membership_path: Path
    clusters_path: Path
    community_count: int = Field(ge=0)
    cluster_count: int = Field(ge=0)
    modularity: float = Field(allow_inf_nan=False)
    timing: float = Field(ge=0)
