from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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

