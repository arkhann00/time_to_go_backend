from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import get_current_user
from src.auth.models.user import User
from src.believers.models.believer import Believer, ChristianStage
from src.believers.schema.believer import (
    BelieverCreate,
    BelieverResponse,
    BelieverUpdate,
    BelieverWithOwnerResponse,
)
from src.believers.services import get_available_method
from src.db.session import get_db

router = APIRouter(prefix="/believers", tags=["Believers"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_believer(
    payload: BelieverCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BelieverResponse:
    method = await get_available_method(
        db, method_id=payload.method_id, user_id=current_user.id
    )
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Метод евангелизации не найден или недоступен.",
        )

    believer = Believer(
        user_id=current_user.id,
        name=payload.name,
        telegram=payload.telegram,
        phone_number=payload.phone_number,
        met_at=payload.met_at,
        stage=payload.stage,
        method_id=payload.method_id,
        note=payload.note,
        testimony=payload.testimony,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    db.add(believer)
    await db.commit()
    believer = await db.scalar(
        select(Believer)
        .where(Believer.id == believer.id, Believer.user_id == current_user.id)
        .options(selectinload(Believer.method))
    )
    return BelieverResponse.model_validate(believer)


@router.get("")
async def list_believers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BelieverResponse]:
    believers = await db.scalars(
        select(Believer)
        .where(Believer.user_id == current_user.id)
        .order_by(Believer.met_at.desc())
        .options(selectinload(Believer.method))
    )
    return [BelieverResponse.model_validate(item) for item in believers]


@router.get("/my")
async def list_my_believers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BelieverResponse]:
    believers = await db.scalars(
        select(Believer)
        .where(Believer.user_id == current_user.id)
        .order_by(Believer.met_at.desc())
        .options(selectinload(Believer.method))
    )
    return [BelieverResponse.model_validate(item) for item in believers]


@router.get("/all")
async def list_all_believers(
    db: AsyncSession = Depends(get_db),
) -> list[BelieverWithOwnerResponse]:
    believers = await db.scalars(
        select(Believer)
        .order_by(Believer.met_at.desc())
        .options(selectinload(Believer.method), selectinload(Believer.owner))
    )
    return [BelieverWithOwnerResponse.model_validate(item) for item in believers]


@router.get("/testimony-of-day")
async def testimony_of_day(
    day: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> BelieverWithOwnerResponse:
    target_day = day or date.today()

    testimony_filter = (Believer.testimony.is_not(None), Believer.testimony != "")
    total_with_testimony = await db.scalar(
        select(func.count(Believer.id)).where(*testimony_filter)
    )
    if not total_with_testimony:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Нет новообращенных со свидетельством.",
        )

    day_index = target_day.toordinal() % total_with_testimony
    believer = await db.scalar(
        select(Believer)
        .where(*testimony_filter)
        .order_by(Believer.id)
        .offset(day_index)
        .limit(1)
        .options(selectinload(Believer.method), selectinload(Believer.owner))
    )
    return BelieverWithOwnerResponse.model_validate(believer)


@router.get("/stats/accepted-jesus-count")
async def accepted_jesus_count(
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    total = await db.scalar(
        select(func.count(Believer.id)).where(Believer.stage != ChristianStage.INTERESTED)
    )
    return {"count": total or 0}


@router.get("/latest")
async def latest_believers(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[BelieverWithOwnerResponse]:
    stmt = select(Believer).options(selectinload(Believer.method), selectinload(Believer.owner))

    if date_from is not None:
        stmt = stmt.where(Believer.met_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Believer.met_at <= date_to)

    believers = await db.scalars(stmt.order_by(Believer.met_at.desc()).limit(20))
    return [BelieverWithOwnerResponse.model_validate(item) for item in believers]


@router.get("/{believer_id}")
async def get_believer(
    believer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BelieverResponse:
    believer = await db.scalar(
        select(Believer)
        .where(Believer.id == believer_id, Believer.user_id == current_user.id)
        .options(selectinload(Believer.method))
    )
    if not believer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Новообращенный не найден.",
        )
    return BelieverResponse.model_validate(believer)


@router.patch("/{believer_id}")
async def update_believer(
    believer_id: int,
    payload: BelieverUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BelieverResponse:
    believer = await db.scalar(
        select(Believer).where(
            Believer.id == believer_id,
            Believer.user_id == current_user.id,
        )
    )
    if not believer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Новообращенный не найден.",
        )

    updates = payload.model_dump(exclude_unset=True)
    if "method_id" in updates:
        method = await get_available_method(
            db, method_id=updates["method_id"], user_id=current_user.id
        )
        if not method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Метод евангелизации не найден или недоступен.",
            )

    for field, value in updates.items():
        setattr(believer, field, value)

    await db.commit()
    believer = await db.scalar(
        select(Believer)
        .where(Believer.id == believer_id, Believer.user_id == current_user.id)
        .options(selectinload(Believer.method))
    )
    return BelieverResponse.model_validate(believer)


@router.delete("/{believer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_believer(
    believer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    believer = await db.scalar(
        select(Believer).where(
            Believer.id == believer_id,
            Believer.user_id == current_user.id,
        )
    )
    if not believer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Новообращенный не найден.",
        )

    await db.delete(believer)
    await db.commit()

