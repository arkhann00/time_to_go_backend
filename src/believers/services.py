from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.believers.models.believer import Believer
from src.believers.models.method import EvangelismMethod

DEFAULT_METHOD_NAMES = ("4 знака", "Иисус у двери")


async def ensure_default_methods(db: AsyncSession) -> None:
    existing_defaults = await db.scalars(
        select(EvangelismMethod).where(EvangelismMethod.is_default.is_(True))
    )
    existing_names = {method.name for method in existing_defaults}

    for default_name in DEFAULT_METHOD_NAMES:
        if default_name not in existing_names:
            db.add(EvangelismMethod(name=default_name, is_default=True))

    await db.commit()


def methods_for_user_stmt(user_id: int) -> Select[tuple[EvangelismMethod]]:
    return select(EvangelismMethod).where(
        or_(
            EvangelismMethod.is_default.is_(True),
            EvangelismMethod.user_id == user_id,
        )
    )


async def get_available_method(
    db: AsyncSession, *, method_id: int, user_id: int
) -> EvangelismMethod | None:
    stmt = methods_for_user_stmt(user_id).where(EvangelismMethod.id == method_id)
    return await db.scalar(stmt)


async def get_method_statistic(db: AsyncSession) -> dict:
    believers = (
        await db.scalars(select(Believer).options(selectinload(Believer.method)))
    ).all()

    stat = {method: 0 for method in DEFAULT_METHOD_NAMES}
    stat.setdefault("другой", 0)

    for believer in believers:
        name = believer.method.name if believer.method else "другой"
        if name in stat:
            stat[name] += 1
        else:
            stat["другой"] += 1

    return stat
