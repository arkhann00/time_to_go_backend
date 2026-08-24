from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models.notification_settings import NotificationSettings
from src.auth.models.user import User
from src.auth.schema.user import UserLogin, UserRegister, UserUpdate
from src.auth.security import hash_password, verify_password

ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/heic-sequence": ".heic",
    "image/heif-sequence": ".heif",
}
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024
AVATARS_DIR = Path("uploads/avatars")


async def register_user(data: UserRegister, db: AsyncSession) -> User:
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует.",
        )

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()
    db.add(NotificationSettings(user_id=user.id))
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_profile(user: User, data: UserUpdate, db: AsyncSession) -> User:
    if data.name is not None:
        user.name = data.name
    if data.about is not None:
        user.about = data.about
    await db.commit()
    await db.refresh(user)
    return user


async def save_user_avatar(user: User, avatar: UploadFile, db: AsyncSession) -> User:
    extension = ALLOWED_AVATAR_CONTENT_TYPES.get((avatar.content_type or "").lower())
    if extension is None and avatar.filename:
        suffix = Path(avatar.filename).suffix.lower()
        if suffix in ALLOWED_AVATAR_EXTENSIONS:
            extension = ".jpg" if suffix == ".jpeg" else suffix

    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимы JPEG, PNG, WEBP, GIF, HEIC или HEIF.",
        )

    file_bytes = await avatar.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл аватарки пустой.",
        )
    if len(file_bytes) > MAX_AVATAR_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Размер аватарки не должен превышать 5MB.",
        )

    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"user_{user.id}_{uuid4().hex}{extension}"
    avatar_path = AVATARS_DIR / filename
    avatar_path.write_bytes(file_bytes)

    # Remove previous local avatar file to avoid orphaned uploads.
    if user.avatar_url and user.avatar_url.startswith("/uploads/avatars/"):
        old_avatar_path = Path(user.avatar_url.lstrip("/"))
        if old_avatar_path.exists():
            old_avatar_path.unlink()

    user.avatar_url = f"/uploads/avatars/{filename}"
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(data: UserLogin, db: AsyncSession) -> User:
    user = await db.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
        )
    return user
