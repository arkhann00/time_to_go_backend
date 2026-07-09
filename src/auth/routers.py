from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models.user import User
from src.auth.schema.user import (
    TokenRefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from src.auth.security import create_access_token, decode_token, hash_password
from src.auth.services import (
    authenticate_user,
    register_user,
    save_user_avatar,
    update_user_profile,
)
from src.db.session import get_db


router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
async def register(
    payload: UserRegister, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    user = await register_user(payload, db)
    return UserResponse.model_validate(user)


@router.post("/login")
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await authenticate_user(payload, db)
    token = create_access_token(sub=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/refresh")
async def refresh_access_token(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    subject = decode_token(payload.access_token)
    if not subject or not subject.isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или просроченный access_token.",
        )

    user = await db.scalar(select(User).where(User.id == int(subject)))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден.",
        )

    new_access_token = create_access_token(sub=str(user.id))
    return TokenResponse(access_token=new_access_token)


@router.patch("/me")
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    updated_user = await update_user_profile(current_user, payload, db)
    return UserResponse.model_validate(updated_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await db.delete(current_user)
    await db.commit()


@router.get(
    "/all-users",
    summary="Список всех пользователей (Admin)",
    tags=["Admin"],
)
async def get_all_users(
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    users = (await db.scalars(select(User))).all()
    return [UserResponse.model_validate(u) for u in users]


@router.delete(
    "/by-email",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить аккаунт по email (Admin)",
    tags=["Admin"],
)
async def delete_user_by_email(
    email: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
    await db.delete(user)
    await db.commit()


@router.post("/me/avatar")
async def upload_my_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    updated_user = await save_user_avatar(current_user, avatar, db)
    return UserResponse.model_validate(updated_user)

@router.patch("/me/password")
async def change_password(
    email: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
) -> str:
    current_user = db.scalars(select(User).where(User.email == str(email)))
    current_user.hashed_password = hash_password(new_password)
    await db.commit()
    await db.refresh(current_user)
    return "success"