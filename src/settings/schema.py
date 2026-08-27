from enum import StrEnum

from pydantic import BaseModel, Field


class RegionCheckStatus(StrEnum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"


class RegionWarningReason(StrEnum):
    OUTSIDE_RUSSIA = "outside_russia"
    ANONYMIZER_DETECTED = "anonymizer_detected"


class RegionCheckResponse(BaseModel):
    check_status: RegionCheckStatus
    country_code: str | None = None
    country_name: str | None = None
    region: str | None = None
    city: str | None = None
    is_in_russia: bool | None = None
    vpn_detected: bool | None = None
    proxy_detected: bool | None = None
    tor_detected: bool | None = None
    should_warn: bool = False
    warning_reasons: list[RegionWarningReason] = Field(default_factory=list)
    warning_message: str | None = None
