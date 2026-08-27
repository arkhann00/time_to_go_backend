import httpx
from httpx import AsyncClient


async def test_region_check_in_russia_without_vpn(
    client: AsyncClient, monkeypatch
) -> None:
    async def fake_lookup(_):
        return {
            "is_vpn": False,
            "is_proxy": False,
            "is_tor": False,
            "location": {
                "country": "Russia",
                "country_code": "RU",
                "state": "Moscow",
                "city": "Moscow",
            },
        }

    monkeypatch.setattr("src.settings.handler.lookup_ip", fake_lookup)
    response = await client.get(
        "/settings/region-check", headers={"X-Forwarded-For": "5.255.255.5"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "check_status": "success",
        "country_code": "RU",
        "country_name": "Russia",
        "region": "Moscow",
        "city": "Moscow",
        "is_in_russia": True,
        "vpn_detected": False,
        "proxy_detected": False,
        "tor_detected": False,
        "should_warn": False,
        "warning_reasons": [],
        "warning_message": None,
    }


async def test_region_check_warns_outside_russia_and_for_anonymizer(
    client: AsyncClient, monkeypatch
) -> None:
    async def fake_lookup(_):
        return {
            "is_vpn": True,
            "is_proxy": False,
            "is_tor": False,
            "location": {
                "country": "Germany",
                "country_code": "DE",
                "state": "Hesse",
                "city": "Frankfurt am Main",
            },
        }

    monkeypatch.setattr("src.settings.handler.lookup_ip", fake_lookup)
    response = await client.get(
        "/settings/region-check", headers={"X-Forwarded-For": "8.8.8.8"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_in_russia"] is False
    assert body["vpn_detected"] is True
    assert body["should_warn"] is True
    assert body["warning_reasons"] == [
        "outside_russia",
        "anonymizer_detected",
    ]
    assert body["warning_message"]


async def test_region_check_returns_unavailable_for_local_ip(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/settings/region-check", headers={"X-Forwarded-For": "127.0.0.1"}
    )

    assert response.status_code == 200
    assert response.json()["check_status"] == "unavailable"
    assert response.json()["should_warn"] is False
    assert response.json()["is_in_russia"] is None


async def test_region_check_does_not_fail_when_provider_is_unavailable(
    client: AsyncClient, monkeypatch
) -> None:
    async def fake_lookup(_):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("src.settings.handler.lookup_ip", fake_lookup)
    response = await client.get(
        "/settings/region-check", headers={"X-Forwarded-For": "1.1.1.1"}
    )

    assert response.status_code == 200
    assert response.json()["check_status"] == "unavailable"
    assert response.json()["should_warn"] is False
