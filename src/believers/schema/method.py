from pydantic import BaseModel, ConfigDict


class MethodCreate(BaseModel):
    name: str


class MethodResponse(BaseModel):
    id: int
    name: str
    is_default: bool

    model_config = ConfigDict(from_attributes=True)
