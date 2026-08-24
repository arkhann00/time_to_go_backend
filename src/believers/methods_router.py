from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models.user import User
from src.believers.models.method import EvangelismMethod
from src.believers.schema.method import MethodCreate, MethodResponse
from src.believers.services import get_method_statistic, methods_for_user_stmt
from src.db.session import get_db

router = APIRouter(prefix="/methods", tags=["Evangelism methods"])


@router.get("")
async def list_methods(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MethodResponse]:
    methods = await db.scalars(
        methods_for_user_stmt(current_user.id).order_by(EvangelismMethod.name)
    )
    return [MethodResponse.model_validate(method) for method in methods]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_method(
    payload: MethodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MethodResponse:
    normalized_name = payload.name.strip()
    if not normalized_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Название метода не может быть пустым.",
        )

    duplicate_stmt = select(EvangelismMethod).where(
        EvangelismMethod.user_id == current_user.id,
        EvangelismMethod.name == normalized_name,
    )
    duplicate = await db.scalar(duplicate_stmt)
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Такой метод уже существует.",
        )

    method = EvangelismMethod(
        name=normalized_name,
        user_id=current_user.id,
        is_default=False,
    )
    db.add(method)
    await db.commit()
    await db.refresh(method)
    return MethodResponse.model_validate(method)


@router.get("/statistics")
async def fetch_method_statistic(db: AsyncSession = Depends(get_db)):
    return await get_method_statistic(db=db)
