import asyncio
import json
import os
from functools import lru_cache, partial

import firebase_admin
from firebase_admin import credentials, messaging

PUSH_TITLE = "Время идти 🙌"
PUSH_BODY = "Напиши своим ребятам и пригласи их в церковь."


@lru_cache(maxsize=1)
def get_firebase_app() -> firebase_admin.App | None:
    """Initialise Firebase only when credentials were deliberately configured."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    raw_credentials = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    credentials_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if raw_credentials:
        certificate = credentials.Certificate(json.loads(raw_credentials))
    elif credentials_path:
        certificate = credentials.Certificate(credentials_path)
    else:
        return None
    return firebase_admin.initialize_app(certificate)


async def send_believers_friday_reminder(token: str) -> None:
    app = get_firebase_app()
    if app is None:
        raise RuntimeError("Firebase credentials are not configured.")

    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=PUSH_TITLE, body=PUSH_BODY),
        data={"type": "believers_friday_reminder", "screen": "believers"},
        android=messaging.AndroidConfig(
            notification=messaging.AndroidNotification(channel_id="general")
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))
        ),
    )
    await asyncio.to_thread(partial(messaging.send, message, app=app))


def is_invalid_fcm_token_error(error: Exception) -> bool:
    """Recognise permanent FCM registration failures without retrying the token."""
    invalid_error_types = tuple(
        item
        for item in (
            getattr(messaging, "UnregisteredError", None),
            getattr(messaging, "SenderIdMismatchError", None),
        )
        if item is not None
    )
    if invalid_error_types and isinstance(error, invalid_error_types):
        return True
    return "registration-token-not-registered" in str(error).lower()
