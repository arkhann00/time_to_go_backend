from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import get_current_user, get_optional_user
from src.auth.models.user import User
from src.believers.models.believer import Believer
from src.db.session import get_db
from src.outreach.models.outreach_statistics import OutreachStatistics
from src.outreach.models.testimony import Testimony
from src.outreach.schema.outreach_statistics import (
    OutreachStatisticsAdd,
    OutreachStatisticsResponse,
    OutreachStatisticsUpdate,
    OutreachStatisticsWithUserResponse,
    StatisticsType,
    SummaryStatisticsResponse,
)

router = APIRouter(prefix="/outreach-statistics", tags=["Outreach statistics"])


@router.get("/summary")
async def get_summary_statistics(
    type: StatisticsType = Query(default=StatisticsType.general),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> SummaryStatisticsResponse:
    if type == StatisticsType.personal and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Авторизация обязательна для личной статистики.",
        )

    user_filter_believers = (
        [Believer.user_id == current_user.id]
        if type == StatisticsType.personal
        else []
    )
    user_filter_stats = (
        [OutreachStatistics.user_id == current_user.id]
        if type == StatisticsType.personal
        else []
    )

    believers_count = await db.scalar(
        select(func.count(Believer.id)).where(*user_filter_believers)
    ) or 0

    believers_with_contact = await db.scalar(
        select(func.count(Believer.id)).where(
            *user_filter_believers,
            or_(
                Believer.telegram.isnot(None),
                Believer.phone_number.isnot(None),
            ),
        )
    ) or 0

    believers_no_contact = await db.scalar(
        select(func.count(Believer.id)).where(
            *user_filter_believers,
            Believer.telegram.is_(None),
            Believer.phone_number.is_(None),
        )
    ) or 0

    stats_row = await db.execute(
        select(
            func.coalesce(func.sum(OutreachStatistics.gospels_told), 0),
            func.coalesce(func.sum(OutreachStatistics.scriptures_distributed), 0),
            func.coalesce(func.sum(OutreachStatistics.healings_deliverances), 0),
        ).where(*user_filter_stats)
    )
    gospels_told_sum, scriptures_distributed_sum, healings_deliverances_sum = (
        stats_row.one()
    )

    return SummaryStatisticsResponse(
        total_heard_gospel=believers_count + gospels_told_sum,
        heard_gospel_no_contact=gospels_told_sum + believers_no_contact,
        heard_gospel_has_contact=believers_with_contact,
        scriptures_distributed=scriptures_distributed_sum,
        healings_deliverances=healings_deliverances_sum,
    )


async def _get_or_create_statistics(
    user_id: int, db: AsyncSession
) -> OutreachStatistics:
    statistics = await db.scalar(
        select(OutreachStatistics).where(OutreachStatistics.user_id == user_id)
    )
    if not statistics:
        statistics = OutreachStatistics(user_id=user_id)
        db.add(statistics)
        await db.commit()
        await db.refresh(statistics)
    return statistics


@router.get("/me")
async def get_my_outreach_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutreachStatisticsResponse:
    statistics = await _get_or_create_statistics(current_user.id, db)
    return OutreachStatisticsResponse.model_validate(statistics)


@router.post("/add")
async def add_outreach_statistics(
    payload: OutreachStatisticsAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutreachStatisticsResponse:
    statistics = await _get_or_create_statistics(current_user.id, db)
    statistics.gospels_told += payload.gospels_told
    statistics.salvation_prayed_unreachable += payload.salvation_prayed_unreachable
    statistics.scriptures_distributed += payload.scriptures_distributed
    statistics.healings_deliverances += payload.healings_deliverances
    if payload.testimony is not None:
        db.add(Testimony(outreach_statistics_id=statistics.id, text=payload.testimony))
    await db.commit()
    await db.refresh(statistics)
    return OutreachStatisticsResponse.model_validate(statistics)


@router.patch("/me")
async def update_outreach_statistics(
    payload: OutreachStatisticsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutreachStatisticsResponse:
    statistics = await _get_or_create_statistics(current_user.id, db)
    update_data = payload.model_dump(exclude_unset=True)
    delete_testimony_id = update_data.pop("delete_testimony_id", None)
    for field, value in update_data.items():
        setattr(statistics, field, value)
    if delete_testimony_id is not None:
        testimony = await db.scalar(
            select(Testimony).where(
                Testimony.id == delete_testimony_id,
                Testimony.outreach_statistics_id == statistics.id,
            )
        )
        if testimony is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Свидетельство не найдено.",
            )
        await db.delete(testimony)
    await db.commit()
    await db.refresh(statistics)
    return OutreachStatisticsResponse.model_validate(statistics)


@router.post("/reset", status_code=status.HTTP_200_OK)
async def reset_outreach_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutreachStatisticsResponse:
    statistics = await _get_or_create_statistics(current_user.id, db)
    statistics.gospels_told = 0
    statistics.salvation_prayed_unreachable = 0
    statistics.scriptures_distributed = 0
    statistics.healings_deliverances = 0
    await db.commit()
    await db.refresh(statistics)
    return OutreachStatisticsResponse.model_validate(statistics)


@router.get("/all")
async def list_all_outreach_statistics(
    db: AsyncSession = Depends(get_db),
) -> list[OutreachStatisticsWithUserResponse]:
    result = await db.scalars(
        select(OutreachStatistics).options(
            selectinload(OutreachStatistics.owner),
            selectinload(OutreachStatistics.testimonies),
        )
    )
    return [
        OutreachStatisticsWithUserResponse(
            id=item.id,
            user_id=item.user_id,
            gospels_told=item.gospels_told,
            salvation_prayed_unreachable=item.salvation_prayed_unreachable,
            scriptures_distributed=item.scriptures_distributed,
            healings_deliverances=item.healings_deliverances,
            testimonies=item.testimonies,
            created_at=item.created_at,
            updated_at=item.updated_at,
            user=item.owner,
        )
        for item in result
    ]
