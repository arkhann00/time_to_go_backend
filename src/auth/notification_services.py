from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models.notification_settings import NotificationSettings
from src.auth.models.push_device import PushDevice
from src.auth.models.user import User
from src.auth.schema.notifications import PushDeviceUpsert
from src.notifications.fcm import (
    is_invalid_fcm_token_error,
    send_believers_friday_reminder,
)


async def get_or_create_notification_settings(
    user_id: int, db: AsyncSession
) -> NotificationSettings:
    settings = await db.scalar(
        select(NotificationSettings).where(NotificationSettings.user_id == user_id)
    )
    if settings is None:
        settings = NotificationSettings(user_id=user_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def upsert_push_device(
    user: User, payload: PushDeviceUpsert, db: AsyncSession
) -> PushDevice:
    device = await db.scalar(
        select(PushDevice).where(PushDevice.token == payload.token)
    )
    if device is None:
        device = PushDevice(
            user_id=user.id,
            token=payload.token,
            platform=payload.platform,
            timezone=payload.timezone,
            enabled=True,
        )
        db.add(device)
    else:
        # Tokens can change owner when a user signs in on a shared/reinstalled device.
        device.user_id = user.id
        device.platform = payload.platform
        device.timezone = payload.timezone
        device.enabled = True
    await db.commit()
    await db.refresh(device)
    return device


async def delete_push_device(user_id: int, token: str, db: AsyncSession) -> bool:
    device = await db.scalar(
        select(PushDevice).where(
            PushDevice.user_id == user_id, PushDevice.token == token
        )
    )
    if device is None:
        return False
    await db.delete(device)
    await db.commit()
    return True


async def send_test_push_notification(user_id: int, db: AsyncSession) -> int:
    """Send the Friday reminder payload immediately, regardless of schedule rules."""
    devices = (
        await db.scalars(
            select(PushDevice).where(
                PushDevice.user_id == user_id,
                PushDevice.enabled.is_(True),
            )
        )
    ).all()
    if not devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Нет активных push-устройств.",
        )

    sent_count = 0
    for device in devices:
        try:
            await send_believers_friday_reminder(device.token)
            sent_count += 1
        except Exception as error:
            if is_invalid_fcm_token_error(error):
                device.enabled = False
                continue
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Не удалось отправить тестовое уведомление.",
            ) from error
    await db.commit()
    return sent_count
