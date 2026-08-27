from fastapi import APIRouter, Request

from src.settings.handler import check_request_region
from src.settings.schema import RegionCheckResponse

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "/region-check",
    summary="Проверить регион и наличие VPN/прокси по IP",
)
async def region_check(request: Request) -> RegionCheckResponse:
    """Return a non-blocking warning decision for the mobile application."""
    return await check_request_region(request)
