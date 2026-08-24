from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Пароль слишком длинный. Максимум 72 байта.")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Пароль слишком длинный. Максимум 72 байта.")
        return value


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: str | None = None
    about: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    access_token: str


class UserUpdate(BaseModel):
    name: str | None = None
    about: str | None = None
