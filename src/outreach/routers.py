from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import get_current_user
from src.auth.models.user import User
from src.db.session import get_db
from src.outreach.models.outreach_statistics import OutreachStatistics
from src.outreach.schema.outreach_statistics import (
    OutreachStatisticsCreate,
    OutreachStatisticsResponse,
    OutreachStatisticsUpdate,
    OutreachStatisticsWithUserResponse,
)

router = APIRouter(prefix="/outreach-statistics", tags=["Outreach statistics"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_outreach_statistics(
    payload: OutreachStatisticsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutreachStatisticsResponse:
    statistics = OutreachStatistics(
        user_id=current_user.id,
        outreach_date=payload.outreach_date,
        gospels_told=payload.gospels_told,
        salvation_prayed_unreachable=payload.salvation_prayed_unreachable,
        scriptures_distributed=payload.scriptures_distributed,
        healings_deliverances=payload.healings_deliverances,
    )
    db.add(statistics)
    await db.commit()
    await db.refresh(statistics)
    return OutreachStatisticsResponse.model_validate(statistics)


@router.get("/me")
async def get_my_outreach_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OutreachStatisticsResponse]:
    result = await db.scalars(
        select(OutreachStatistics)
        .where(OutreachStatistics.user_id == current_user.id)
        .order_by(OutreachStatistics.outreach_date.desc())
    )
    return [OutreachStatisticsResponse.model_validate(item) for item in result]


@router.get("/all")
async def list_all_outreach_statistics(
    db: AsyncSession = Depends(get_db),
) -> list[OutreachStatisticsWithUserResponse]:
    result = await db.scalars(
        select(OutreachStatistics)
        .options(selectinload(OutreachStatistics.owner))
        .order_by(OutreachStatistics.outreach_date.desc())
    )
    return [
        OutreachStatisticsWithUserResponse(
            id=item.id,
            user_id=item.user_id,
            outreach_date=item.outreach_date,
            gospels_told=item.gospels_told,
            salvation_prayed_unreachable=item.salvation_prayed_unreachable,
            scriptures_distributed=item.scriptures_distributed,
            healings_deliverances=item.healings_deliverances,
            created_at=item.created_at,
            updated_at=item.updated_at,
            user=item.owner,
        )
        for item in result
    ]


@router.get("/{statistics_id}")
async def get_outreach_statistics(
    statistics_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutreachStatisticsResponse:
    statistics = await db.scalar(
        select(OutreachStatistics).where(
            OutreachStatistics.id == statistics_id,
            OutreachStatistics.user_id == current_user.id,
        )
    )
    if not statistics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Статистика аутрича не найдена.",
        )
    return OutreachStatisticsResponse.model_validate(statistics)


@router.patch("/{statistics_id}")
async def update_outreach_statistics(
    statistics_id: int,
    payload: OutreachStatisticsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutreachStatisticsResponse:
    statistics = await db.scalar(
        select(OutreachStatistics).where(
            OutreachStatistics.id == statistics_id,
            OutreachStatistics.user_id == current_user.id,
        )
    )
    if not statistics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Статистика аутрича не найдена.",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(statistics, field, value)

    await db.commit()
    await db.refresh(statistics)
    return OutreachStatisticsResponse.model_validate(statistics)


@router.delete("/{statistics_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outreach_statistics(
    statistics_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    statistics = await db.scalar(
        select(OutreachStatistics).where(
            OutreachStatistics.id == statistics_id,
            OutreachStatistics.user_id == current_user.id,
        )
    )
    if not statistics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Статистика аутрича не найдена.",
        )

    await db.delete(statistics)
    await db.commit()
