from pydantic import BaseModel, ConfigDict, Field


class TreeBuildConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    q_block_size: int = Field(default=512, gt=0)
