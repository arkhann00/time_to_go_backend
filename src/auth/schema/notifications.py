from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from src.auth.models.push_device import PushPlatform


class PushDeviceUpsert(BaseModel):
    token: str
    platform: PushPlatform
    timezone: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("FCM token не может быть пустым.")
        if len(value) > 4096:
            raise ValueError("FCM token слишком длинный.")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Укажите корректный IANA timezone.") from exc
        return value


class PushDeviceDelete(BaseModel):
    token: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("FCM token не может быть пустым.")
        return value


class PushDeviceResponse(BaseModel):
    id: int
    platform: PushPlatform
    timezone: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminPushDeviceTokenResponse(BaseModel):
    """Temporary response that exposes the raw FCM token for manual testing."""

    id: int
    user_id: int
    token: str
    platform: PushPlatform
    timezone: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationSettingsUpdate(BaseModel):
    believers_friday_reminder_enabled: bool | None = None
    believers_friday_reminder_time: time | None = None


class NotificationSettingsResponse(BaseModel):
    believers_friday_reminder_enabled: bool
    believers_friday_reminder_time: time

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("believers_friday_reminder_time")
    def serialize_reminder_time(self, value: time) -> str:
        return value.strftime("%H:%M")
