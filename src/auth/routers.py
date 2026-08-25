import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models.push_device import PushDevice
from src.auth.models.user import User
from src.auth.notification_services import (
    delete_push_device,
    get_or_create_notification_settings,
    send_test_push_notification,
    upsert_push_device,
)
from src.auth.schema.notifications import (
    AdminPushDeviceTokenResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    PushDeviceDelete,
    PushDeviceResponse,
    PushDeviceUpsert,
)
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
from src.notifications.fcm import (
    FirebaseNotConfiguredError,
    send_believers_friday_reminder,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post("/register")
async def register(
    payload: UserRegister, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    user = await register_user(payload, db)
    return UserResponse.model_validate(user)


@router.post("/login")
async def login(
    payload: UserLogin, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = await authenticate_user(payload, db)
    token = create_access_token(sub=str(user.id))
    return TokenResponse(access_token=token)


@router.post("/test-push-notification")
async def send_public_test_push_notification(
    payload: PushDeviceDelete,
) -> dict[str, bool]:
    """Send the standard reminder directly to the supplied FCM token."""
    try:
        await send_believers_friday_reminder(payload.token)
    except FirebaseNotConfiguredError as error:
        logger.error("Test push delivery requested but Firebase is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Отправка уведомлений временно не настроена на сервере.",
        ) from error
    except Exception as error:
        logger.exception("Test push delivery failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не удалось отправить тестовое уведомление.",
        ) from error
    return {"sent": True}


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


@router.get(
    "/admin/push-device-tokens",
    summary="Временный публичный список FCM tokens (небезопасно)",
    tags=["Admin"],
)
async def get_all_push_device_tokens(
    db: AsyncSession = Depends(get_db),
) -> list[AdminPushDeviceTokenResponse]:
    """TODO: remove this endpoint or protect it with an administrator dependency."""
    devices = await db.scalars(select(PushDevice).order_by(PushDevice.id))
    return [AdminPushDeviceTokenResponse.model_validate(device) for device in devices]


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден."
        )
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


@router.put("/me/push-device")
async def put_my_push_device(
    payload: PushDeviceUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushDeviceResponse:
    device = await upsert_push_device(current_user, payload, db)
    return PushDeviceResponse.model_validate(device)


@router.delete("/me/push-device", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_push_device(
    payload: PushDeviceDelete,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await delete_push_device(current_user.id, payload.token, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Push-устройство не найдено.",
        )


@router.post("/me/test-push-notification")
async def send_my_test_push_notification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    sent_to_devices = await send_test_push_notification(current_user.id, db)
    return {"sent_to_devices": sent_to_devices}


@router.get("/me/notification-settings")
async def get_my_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsResponse:
    settings = await get_or_create_notification_settings(current_user.id, db)
    return NotificationSettingsResponse.model_validate(settings)


@router.patch("/me/notification-settings")
async def patch_my_notification_settings(
    payload: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsResponse:
    settings = await get_or_create_notification_settings(current_user.id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    await db.commit()
    await db.refresh(settings)
    return NotificationSettingsResponse.model_validate(settings)


@router.put("/me/password")
async def change_password(
    email: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
) -> str:

    result = await db.execute(select(User).where(User.email == str(email)))
    current_user = result.scalar_one_or_none()

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    current_user.hashed_password = hash_password(new_password)
    await db.commit()
    # await db.refresh(current_user)
    return "success"
