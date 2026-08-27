import asyncio
import os
import time
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Any

import httpx
from fastapi import Request

from src.settings.schema import (
    RegionCheckResponse,
    RegionCheckStatus,
    RegionWarningReason,
)

IPAPI_URL = "https://api.ipapi.is"
CACHE_TTL_SECONDS = 6 * 60 * 60
CACHE_MAX_ITEMS = 4096
REQUEST_TIMEOUT_SECONDS = 3.0

IPAddress = IPv4Address | IPv6Address
_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_cache_lock = asyncio.Lock()


def get_client_ip(request: Request) -> IPAddress | None:
    """Read the original client IP supplied by the trusted reverse proxy."""
    candidates: list[str] = []
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        candidates.extend(forwarded_for.split(","))
    if request.client:
        candidates.append(request.client.host)

    for candidate in candidates:
        try:
            parsed = ip_address(candidate.strip())
        except ValueError:
            continue
        if isinstance(parsed, IPv6Address) and parsed.ipv4_mapped:
            return parsed.ipv4_mapped
        return parsed
    return None


def _is_public_ip(client_ip: IPAddress) -> bool:
    return client_ip.is_global


async def _request_ip_data(client_ip: IPAddress) -> dict[str, Any]:
    params = {"q": str(client_ip)}
    api_key = os.getenv("IPAPI_API_KEY")
    if api_key:
        params["key"] = api_key

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.get(IPAPI_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError("GeoIP provider returned an invalid response")
    return payload


async def lookup_ip(client_ip: IPAddress) -> dict[str, Any]:
    cache_key = str(client_ip)
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    payload = await _request_ip_data(client_ip)
    async with _cache_lock:
        if len(_cache) >= CACHE_MAX_ITEMS:
            oldest_key = min(_cache, key=lambda key: _cache[key][0])
            _cache.pop(oldest_key, None)
        _cache[cache_key] = (now, payload)
    return payload


def _warning_message(reasons: list[RegionWarningReason]) -> str | None:
    outside = RegionWarningReason.OUTSIDE_RUSSIA in reasons
    anonymizer = RegionWarningReason.ANONYMIZER_DETECTED in reasons
    if outside and anonymizer:
        return (
            "Похоже, вы находитесь за пределами России и используете VPN или "
            "прокси. Приложение может работать с перебоями."
        )
    if outside:
        return (
            "Похоже, вы находитесь за пределами России. Приложение может "
            "работать с перебоями."
        )
    if anonymizer:
        return (
            "Обнаружено подключение через VPN или прокси. Приложение может "
            "работать с перебоями."
        )
    return None


def build_region_response(payload: dict[str, Any]) -> RegionCheckResponse:
    location = payload.get("location")
    if not isinstance(location, dict):
        raise TypeError("GeoIP response does not contain location")

    raw_country_code = location.get("country_code")
    if not isinstance(raw_country_code, str) or len(raw_country_code) != 2:
        raise ValueError("GeoIP response does not contain a country code")
    country_code = raw_country_code.upper()

    vpn_detected = payload.get("is_vpn") is True
    proxy_detected = payload.get("is_proxy") is True
    tor_detected = payload.get("is_tor") is True
    is_in_russia = country_code == "RU"

    reasons: list[RegionWarningReason] = []
    if not is_in_russia:
        reasons.append(RegionWarningReason.OUTSIDE_RUSSIA)
    if vpn_detected or proxy_detected or tor_detected:
        reasons.append(RegionWarningReason.ANONYMIZER_DETECTED)

    return RegionCheckResponse(
        check_status=RegionCheckStatus.SUCCESS,
        country_code=country_code,
        country_name=location.get("country"),
        region=location.get("state"),
        city=location.get("city"),
        is_in_russia=is_in_russia,
        vpn_detected=vpn_detected,
        proxy_detected=proxy_detected,
        tor_detected=tor_detected,
        should_warn=bool(reasons),
        warning_reasons=reasons,
        warning_message=_warning_message(reasons),
    )


async def check_request_region(request: Request) -> RegionCheckResponse:
    client_ip = get_client_ip(request)
    if client_ip is None or not _is_public_ip(client_ip):
        return RegionCheckResponse(check_status=RegionCheckStatus.UNAVAILABLE)

    try:
        payload = await lookup_ip(client_ip)
        return build_region_response(payload)
    except (httpx.HTTPError, ValueError, TypeError):
        return RegionCheckResponse(check_status=RegionCheckStatus.UNAVAILABLE)
