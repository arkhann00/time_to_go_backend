from httpx import AsyncClient


async def register_and_login(
    client: AsyncClient, email: str = "user@example.com"
) -> str:
    response = await client.post(
        "/auth/register",
        json={"name": "User", "email": email, "password": "password"},
    )
    assert response.status_code == 200
    response = await client.post(
        "/auth/login", json={"email": email, "password": "password"}
    )
    return response.json()["access_token"]


async def test_register_update_and_delete_push_device(client: AsyncClient) -> None:
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"token": "fcm-token", "platform": "android", "timezone": "Europe/Moscow"}

    response = await client.put("/auth/me/push-device", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["enabled"] is True

    payload["timezone"] = "America/New_York"
    response = await client.put("/auth/me/push-device", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["timezone"] == "America/New_York"

    response = await client.request(
        "DELETE", "/auth/me/push-device", json={"token": "fcm-token"}, headers=headers
    )
    assert response.status_code == 204

    response = await client.request(
        "DELETE", "/auth/me/push-device", json={"token": "fcm-token"}, headers=headers
    )
    assert response.status_code == 404


async def test_notification_settings_defaults_and_update(client: AsyncClient) -> None:
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/auth/me/notification-settings", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "believers_friday_reminder_enabled": True,
        "believers_friday_reminder_time": "18:00",
    }

    response = await client.patch(
        "/auth/me/notification-settings",
        json={
            "believers_friday_reminder_enabled": False,
            "believers_friday_reminder_time": "19:30",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == {
        "believers_friday_reminder_enabled": False,
        "believers_friday_reminder_time": "19:30",
    }


async def test_test_push_notification_ignores_schedule(
    client: AsyncClient, monkeypatch
) -> None:
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.put(
        "/auth/me/push-device",
        json={
            "token": "test-fcm-token",
            "platform": "ios",
            "timezone": "Europe/Moscow",
        },
        headers=headers,
    )
    sent_tokens: list[str] = []

    async def fake_send(device_token: str) -> None:
        sent_tokens.append(device_token)

    monkeypatch.setattr(
        "src.auth.notification_services.send_believers_friday_reminder", fake_send
    )
    response = await client.post("/auth/me/test-push-notification", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"sent_to_devices": 1}
    assert sent_tokens == ["test-fcm-token"]
