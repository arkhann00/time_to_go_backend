from datetime import UTC, date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.auth.models.notification_settings import NotificationSettings
from src.auth.models.push_device import PushDevice, PushPlatform
from src.auth.models.user import User
from src.believers.models.believer import Believer, ChristianStage
from src.believers.models.method import EvangelismMethod
from src.notifications.models import NotificationDelivery
from src.notifications.scheduler import run_friday_reminder_cycle


async def create_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
    token: str,
    timezone: str,
    with_believer: bool = True,
) -> User:
    async with session_factory() as db:
        user = User(name=email, email=email, hashed_password="hash")
        method = EvangelismMethod(name=f"method-{email}", user_id=None, is_default=True)
        db.add_all(
            [
                user,
                method,
                NotificationSettings(
                    owner=user,
                    believers_friday_reminder_enabled=True,
                    believers_friday_reminder_time=time(18, 0),
                ),
                PushDevice(
                    owner=user,
                    token=token,
                    platform=PushPlatform.ANDROID,
                    timezone=timezone,
                    enabled=True,
                ),
            ]
        )
        await db.flush()
        if with_believer:
            db.add(
                Believer(
                    user_id=user.id,
                    name="Believer",
                    met_at=date(2026, 8, 21),
                    stage=ChristianStage.INTERESTED,
                    method_id=method.id,
                    latitude=55.75,
                    longitude=37.62,
                )
            )
        await db.commit()
        return user


async def test_scheduler_selects_user_by_device_local_time(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await create_user(
        session_factory,
        email="moscow@example.com",
        token="moscow-token",
        timezone="Europe/Moscow",
    )
    await create_user(
        session_factory,
        email="new-york@example.com",
        token="new-york-token",
        timezone="America/New_York",
    )
    delivered: list[str] = []

    async def sender(token: str) -> None:
        delivered.append(token)

    count = await run_friday_reminder_cycle(
        now=datetime(2026, 8, 21, 15, 0, tzinfo=UTC),
        session_factory=session_factory,
        sender=sender,
    )

    assert count == 1
    assert delivered == ["moscow-token"]


async def test_scheduler_skips_users_without_believers(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await create_user(
        session_factory,
        email="empty@example.com",
        token="empty-token",
        timezone="Europe/Moscow",
        with_believer=False,
    )
    delivered: list[str] = []

    count = await run_friday_reminder_cycle(
        now=datetime(2026, 8, 21, 15, 0, tzinfo=UTC),
        session_factory=session_factory,
        sender=lambda token: _append(delivered, token),
    )

    assert count == 0
    assert delivered == []


async def test_scheduler_deduplicates_friday_delivery(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = await create_user(
        session_factory,
        email="dedupe@example.com",
        token="dedupe-token",
        timezone="Europe/Moscow",
    )
    delivered: list[str] = []

    first = await run_friday_reminder_cycle(
        now=datetime(2026, 8, 21, 15, 0, tzinfo=UTC),
        session_factory=session_factory,
        sender=lambda token: _append(delivered, token),
    )
    second = await run_friday_reminder_cycle(
        now=datetime(2026, 8, 21, 15, 5, tzinfo=UTC),
        session_factory=session_factory,
        sender=lambda token: _append(delivered, token),
    )

    async with session_factory() as db:
        delivery_count = await db.scalar(
            select(func.count(NotificationDelivery.id)).where(
                NotificationDelivery.user_id == user.id
            )
        )
    assert first == 1
    assert second == 0
    assert delivered == ["dedupe-token"]
    assert delivery_count == 1


async def _append(items: list[str], value: str) -> None:
    items.append(value)
