from pydantic import BaseModel, ConfigDict, Field


class ClusterConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    num_clusters: int | None = Field(default=None, ge=1)
