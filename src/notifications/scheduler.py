import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.auth.models.notification_settings import NotificationSettings
from src.auth.models.push_device import PushDevice
from src.believers.models.believer import Believer
from src.db.session import SessionLocal
from src.notifications.fcm import (
    is_invalid_fcm_token_error,
    send_believers_friday_reminder,
    send_new_believer_follow_up,
)
from src.notifications.models import NotificationDelivery

logger = logging.getLogger(__name__)
REMINDER_TYPE = "believers_friday_reminder"
NEW_BELIEVER_FOLLOW_UP_TYPE_PREFIX = "new_believer_follow_up"
REMINDER_CHECK_INTERVAL_MINUTES = 15

PushSender = Callable[[str], Awaitable[None]]
FollowUpPushSender = Callable[[str, str], Awaitable[None]]


def is_reminder_due(
    now: datetime, reminder_time: time, device_timezone: str
) -> tuple[bool, datetime]:
    """Return whether a device is within this scheduler's delivery window."""
    local_now = now.astimezone(ZoneInfo(device_timezone))
    if local_now.weekday() != 5:  # Saturday
        return False, local_now
    scheduled = datetime.combine(
        local_now.date(), reminder_time, tzinfo=local_now.tzinfo
    )
    due = (
        scheduled
        <= local_now
        < scheduled + timedelta(minutes=REMINDER_CHECK_INTERVAL_MINUTES)
    )
    return due, local_now


async def _claim_delivery(
    db: AsyncSession,
    user_id: int,
    notification_type: str,
    local_date: date,
) -> bool:
    db.add(
        NotificationDelivery(
            user_id=user_id,
            notification_type=notification_type,
            local_date=local_date,
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False
    return True


async def run_friday_reminder_cycle(
    *,
    now: datetime | None = None,
    session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
    sender: PushSender = send_believers_friday_reminder,
) -> int:
    """Send one weekly reminder per eligible user and return claimed deliveries.

    The database uniqueness constraint is the cross-process lock: a delivery is claimed
    before FCM is called, so concurrent API instances cannot duplicate a Saturday push.
    """
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")

    sent_count = 0
    async with session_factory() as db:
        rows = await db.execute(
            select(NotificationSettings, PushDevice)
            .join(PushDevice, PushDevice.user_id == NotificationSettings.user_id)
            .where(
                NotificationSettings.believers_friday_reminder_enabled.is_(True),
                PushDevice.enabled.is_(True),
            )
            .order_by(PushDevice.updated_at.desc())
        )
        due_users: dict[int, date] = {}
        for settings, device in rows.all():
            if settings.user_id in due_users:
                continue
            due, local_now = is_reminder_due(
                now, settings.believers_friday_reminder_time, device.timezone
            )
            if due:
                due_users[settings.user_id] = local_now.date()

        for user_id, local_date in due_users.items():
            has_believers = await db.scalar(
                select(Believer.id).where(Believer.user_id == user_id).limit(1)
            )
            if has_believers is None:
                continue
            if not await _claim_delivery(db, user_id, REMINDER_TYPE, local_date):
                continue

            devices = await db.scalars(
                select(PushDevice).where(
                    PushDevice.user_id == user_id, PushDevice.enabled.is_(True)
                )
            )
            for device in devices:
                try:
                    await sender(device.token)
                except (
                    Exception
                ) as error:  # Firebase has several permanent error classes.
                    if is_invalid_fcm_token_error(error):
                        device.enabled = False
                        logger.info(
                            "Disabled invalid FCM token for device %s", device.id
                        )
                    else:
                        logger.exception(
                            "Failed to send FCM push to device %s", device.id
                        )
            await db.commit()
            sent_count += 1
    return sent_count


def _new_believer_follow_up_type(believer_id: int) -> str:
    """Make the delivery journal unique for each believer, not just each user."""
    return f"{NEW_BELIEVER_FOLLOW_UP_TYPE_PREFIX}:{believer_id}"


async def run_new_believer_follow_up_cycle(
    *,
    now: datetime | None = None,
    session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
    sender: FollowUpPushSender = send_new_believer_follow_up,
) -> int:
    """Send one follow-up reminder for every believer added at least 24 hours ago.

    The per-believer type in ``notification_deliveries`` provides an atomic claim,
    so the reminder cannot be duplicated by concurrent scheduler processes.
    """
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")

    eligible_before = now - timedelta(hours=24)
    sent_count = 0
    async with session_factory() as db:
        believers = (
            await db.scalars(
                select(Believer)
                .where(Believer.created_at <= eligible_before)
                .order_by(Believer.created_at)
            )
        ).all()
        for believer in believers:
            devices = (
                await db.scalars(
                    select(PushDevice).where(
                        PushDevice.user_id == believer.user_id,
                        PushDevice.enabled.is_(True),
                    )
                )
            ).all()
            if not devices:
                continue

            if not await _claim_delivery(
                db,
                believer.user_id,
                _new_believer_follow_up_type(believer.id),
                now.date(),
            ):
                continue

            for device in devices:
                try:
                    await sender(device.token, believer.name)
                except Exception as error:  # Firebase has several permanent error classes.
                    if is_invalid_fcm_token_error(error):
                        device.enabled = False
                        logger.info("Disabled invalid FCM token for device %s", device.id)
                    else:
                        logger.exception(
                            "Failed to send new-believer follow-up to device %s",
                            device.id,
                        )
            await db.commit()
            sent_count += 1
    return sent_count


async def run_scheduler_forever() -> None:
    """Standalone scheduler entrypoint for a separate production process."""
    while True:
        try:
            await run_friday_reminder_cycle()
            await run_new_believer_follow_up_cycle()
        except Exception:
            logger.exception("Push notification scheduler cycle failed")
        await asyncio.sleep(REMINDER_CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_scheduler_forever())
