from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.auth.schema.user import UserResponse


class StatisticsType(str, Enum):
    personal = "personal"
    general = "general"


class SummaryStatisticsResponse(BaseModel):
    total_heard_gospel: int
    heard_gospel_no_contact: int
    heard_gospel_has_contact: int
    scriptures_distributed: int
    healings_deliverances: int


class OutreachStatisticsAdd(BaseModel):
    gospels_told: int = Field(default=0, ge=0)
    salvation_prayed_unreachable: int = Field(default=0, ge=0)
    scriptures_distributed: int = Field(default=0, ge=0)
    healings_deliverances: int = Field(default=0, ge=0)


class OutreachStatisticsUpdate(BaseModel):
    gospels_told: int | None = Field(default=None, ge=0)
    salvation_prayed_unreachable: int | None = Field(default=None, ge=0)
    scriptures_distributed: int | None = Field(default=None, ge=0)
    healings_deliverances: int | None = Field(default=None, ge=0)


class OutreachStatisticsResponse(BaseModel):
    id: int
    user_id: int
    gospels_told: int
    salvation_prayed_unreachable: int
    scriptures_distributed: int
    healings_deliverances: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutreachStatisticsWithUserResponse(OutreachStatisticsResponse):
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)
