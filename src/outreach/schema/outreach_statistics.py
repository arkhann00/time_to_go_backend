from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.auth.schema.user import UserResponse


class OutreachStatisticsBase(BaseModel):
    gospels_told: int = Field(default=0, ge=0)
    salvation_prayed_unreachable: int = Field(default=0, ge=0)
    scriptures_distributed: int = Field(default=0, ge=0)
    healings_deliverances: int = Field(default=0, ge=0)


class OutreachStatisticsCreate(OutreachStatisticsBase):
    pass


class OutreachStatisticsUpdate(BaseModel):
    gospels_told: int | None = Field(default=None, ge=0)
    salvation_prayed_unreachable: int | None = Field(default=None, ge=0)
    scriptures_distributed: int | None = Field(default=None, ge=0)
    healings_deliverances: int | None = Field(default=None, ge=0)


class OutreachStatisticsResponse(OutreachStatisticsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutreachStatisticsWithUserResponse(OutreachStatisticsResponse):
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)
