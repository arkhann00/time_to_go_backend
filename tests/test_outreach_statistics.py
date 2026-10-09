from datetime import date

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.auth.models.user import User
from src.believers.models.believer import Believer, ChristianStage
from src.believers.models.method import EvangelismMethod


async def test_general_summary_adds_historical_corrections_to_database_values(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await client.post(
        "/auth/register",
        json={"name": "User", "email": "stats@example.com", "password": "password"},
    )
    login_response = await client.post(
        "/auth/login",
        json={"email": "stats@example.com", "password": "password"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    add_response = await client.post(
        "/outreach-statistics/add",
        json={"gospels_told": 7},
        headers=headers,
    )
    assert add_response.status_code == 200

    async with session_factory() as session:
        user = await session.scalar(
            select(User).where(User.email == "stats@example.com")
        )
        assert user is not None
        method = EvangelismMethod(name="Test method", is_default=True)
        session.add(method)
        await session.flush()
        session.add(
            Believer(
                user_id=user.id,
                name="Contact",
                telegram="@contact",
                phone_number=None,
                met_at=date(2026, 10, 9),
                stage=ChristianStage.INTERESTED,
                method_id=method.id,
                note=None,
                testimony=None,
                latitude=55.75,
                longitude=37.62,
            )
        )
        await session.commit()

    general_response = await client.get("/outreach-statistics/summary")
    assert general_response.status_code == 200
    assert general_response.json()["total_heard_gospel"] == 173
    assert general_response.json()["contacts_taken"] == 57

    personal_response = await client.get(
        "/outreach-statistics/summary?type=personal",
        headers=headers,
    )
    assert personal_response.status_code == 200
    assert personal_response.json()["total_heard_gospel"] == 8
    assert personal_response.json()["contacts_taken"] == 1
