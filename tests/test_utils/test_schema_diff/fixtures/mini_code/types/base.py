from pydantic import BaseModel, ConfigDict


class MaxObject(BaseModel):
    model_config = ConfigDict(extra="allow")
