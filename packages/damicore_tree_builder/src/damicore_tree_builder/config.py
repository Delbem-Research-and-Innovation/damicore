from pydantic import BaseModel, ConfigDict, Field


class TreeBuildConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    q_block_size: int = Field(default=512, gt=0)
