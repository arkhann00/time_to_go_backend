from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import get_current_user
from src.auth.models.user import User
from src.believers.models.believer import Believer
from src.believers.schema.believer import (
    BelieverCreate,
    BelieverResponse,
    BelieverUpdate,
)
from src.believers.services import get_available_method
from src.db.session import get_db

router = APIRouter(prefix="/believers", tags=["Believers"])


def _ensure_has_contact(telegram: str | None, phone_number: str | None) -> None:
    if not telegram and not phone_number:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Укажите хотя бы telegram или номер телефона.",
        )


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

    _ensure_has_contact(believer.telegram, believer.phone_number)

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

