from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from src.believers.models.believer import ChristianStage
from src.believers.schema.method import MethodResponse


class BelieverBase(BaseModel):
    name: str
    telegram: str | None = None
    phone_number: str | None = None
    met_at: date
    stage: ChristianStage
    method_id: int
    note: str | None = None
    testimony: str | None = None
    latitude: float
    longitude: float

    @field_validator("telegram", "phone_number", mode="before")
    @classmethod
    def empty_strings_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

class BelieverCreate(BelieverBase):
    pass


class BelieverUpdate(BaseModel):
    name: str | None = None
    telegram: str | None = None
    phone_number: str | None = None
    met_at: date | None = None
    stage: ChristianStage | None = None
    method_id: int | None = None
    note: str | None = None
    testimony: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("telegram", "phone_number", mode="before")
    @classmethod
    def empty_strings_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

class BelieverResponse(BaseModel):
    id: int
    name: str
    telegram: str | None
    phone_number: str | None
    met_at: date
    stage: ChristianStage
    note: str | None
    testimony: str | None
    latitude: float
    longitude: float
    method: MethodResponse

    model_config = ConfigDict(from_attributes=True)

