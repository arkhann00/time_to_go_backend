from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.auth.models.notification_settings import NotificationSettings
from src.auth.models.push_device import PushDevice, PushPlatform
from src.auth.models.user import User
from src.believers.models.believer import Believer, ChristianStage
from src.believers.models.method import EvangelismMethod
from src.notifications.models import NotificationDelivery
from src.notifications.scheduler import (
    run_friday_reminder_cycle,
    run_new_believer_follow_up_cycle,
)


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
                    believers_friday_reminder_time=time(10, 0),
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
        now=datetime(2026, 8, 22, 7, 0, tzinfo=UTC),
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
        now=datetime(2026, 8, 22, 7, 0, tzinfo=UTC),
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
        now=datetime(2026, 8, 22, 7, 0, tzinfo=UTC),
        session_factory=session_factory,
        sender=lambda token: _append(delivered, token),
    )
    second = await run_friday_reminder_cycle(
        now=datetime(2026, 8, 22, 7, 5, tzinfo=UTC),
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


async def test_new_believer_follow_up_is_sent_after_24_hours_once(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = await create_user(
        session_factory,
        email="follow-up@example.com",
        token="follow-up-token",
        timezone="Europe/Moscow",
        with_believer=False,
    )
    added_at = datetime(2026, 8, 21, 7, 0, tzinfo=UTC)
    async with session_factory() as db:
        method = await db.scalar(
            select(EvangelismMethod).where(EvangelismMethod.is_default.is_(True))
        )
        assert method is not None
        believer = Believer(
            user_id=user.id,
            name="Алексей",
            met_at=date(2026, 8, 21),
            stage=ChristianStage.INTERESTED,
            method_id=method.id,
            latitude=55.75,
            longitude=37.62,
            created_at=added_at,
        )
        db.add(believer)
        await db.commit()
        believer_id = believer.id

    delivered: list[tuple[str, str]] = []

    async def sender(token: str, name: str) -> None:
        delivered.append((token, name))

    first = await run_new_believer_follow_up_cycle(
        now=added_at + timedelta(hours=24),
        session_factory=session_factory,
        sender=sender,
    )
    second = await run_new_believer_follow_up_cycle(
        now=added_at + timedelta(hours=24, minutes=15),
        session_factory=session_factory,
        sender=sender,
    )
    next_day = await run_new_believer_follow_up_cycle(
        now=added_at + timedelta(days=2),
        session_factory=session_factory,
        sender=sender,
    )

    async with session_factory() as db:
        delivery_count = await db.scalar(
            select(func.count(NotificationDelivery.id)).where(
                NotificationDelivery.user_id == user.id,
                NotificationDelivery.notification_type
                == f"new_believer_follow_up:{believer_id}",
            )
        )
    assert first == 1
    assert second == 0
    assert next_day == 0
    assert delivered == [("follow-up-token", "Алексей")]
    assert delivery_count == 1


async def test_follow_up_skips_existing_delivery_and_continues_cycle(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    already_notified = await create_user(
        session_factory,
        email="already@example.com",
        token="already-token",
        timezone="Europe/Moscow",
    )
    await create_user(
        session_factory,
        email="pending@example.com",
        token="pending-token",
        timezone="Europe/Moscow",
    )
    now = datetime(2026, 8, 24, 7, 0, tzinfo=UTC)
    async with session_factory() as db:
        believers = (
            await db.scalars(select(Believer).order_by(Believer.user_id))
        ).all()
        existing, pending = believers
        existing.created_at = now - timedelta(days=3)
        pending.created_at = now - timedelta(days=2)
        db.add(
            NotificationDelivery(
                user_id=already_notified.id,
                notification_type=f"new_believer_follow_up:{existing.id}",
                local_date=now.date(),
            )
        )
        await db.commit()

    delivered: list[tuple[str, str]] = []
    count = await run_new_believer_follow_up_cycle(
        now=now,
        session_factory=session_factory,
        sender=lambda token, name: _append_follow_up(delivered, token, name),
    )
    next_day = await run_new_believer_follow_up_cycle(
        now=now + timedelta(days=1),
        session_factory=session_factory,
        sender=lambda token, name: _append_follow_up(delivered, token, name),
    )

    assert count == 1
    assert next_day == 0
    assert delivered == [("pending-token", "Believer")]


async def test_new_believer_follow_up_waits_full_24_hours(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = await create_user(
        session_factory,
        email="too-soon@example.com",
        token="too-soon-token",
        timezone="Europe/Moscow",
        with_believer=False,
    )
    added_at = datetime(2026, 8, 21, 7, 0, tzinfo=UTC)
    async with session_factory() as db:
        method = await db.scalar(
            select(EvangelismMethod).where(EvangelismMethod.is_default.is_(True))
        )
        assert method is not None
        db.add(
            Believer(
                user_id=user.id,
                name="Мария",
                met_at=date(2026, 8, 21),
                stage=ChristianStage.INTERESTED,
                method_id=method.id,
                latitude=55.75,
                longitude=37.62,
                created_at=added_at,
            )
        )
        await db.commit()

    delivered: list[tuple[str, str]] = []
    count = await run_new_believer_follow_up_cycle(
        now=added_at + timedelta(hours=23, minutes=59),
        session_factory=session_factory,
        sender=lambda token, name: _append_follow_up(delivered, token, name),
    )

    assert count == 0
    assert delivered == []


async def _append(items: list[str], value: str) -> None:
    items.append(value)


async def _append_follow_up(
    items: list[tuple[str, str]], token: str, name: str
) -> None:
    items.append((token, name))
