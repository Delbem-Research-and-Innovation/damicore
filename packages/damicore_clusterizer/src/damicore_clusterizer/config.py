from pydantic import BaseModel, ConfigDict, Field


class ClusterConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    num_clusters: int | None = Field(default=None, ge=1)
