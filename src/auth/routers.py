from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models.user import User
from src.auth.schema.user import TokenResponse, UserLogin, UserRegister, UserResponse
from src.auth.security import create_access_token
from src.auth.services import authenticate_user, register_user
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