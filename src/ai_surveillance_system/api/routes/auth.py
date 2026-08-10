from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.db.session import get_db
from ai_surveillance_system.db.models import User
from ai_surveillance_system.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    UserResponse, RefreshRequest,
)
from ai_surveillance_system.services.auth_service import auth_service
from ai_surveillance_system.api.deps import get_current_active_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        db=db,
    )
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT tokens",
)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate(body.email, body.password, db)
    return auth_service.issue_tokens(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange refresh token for new access token",
)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.refresh_access_token(body.refresh_token, db)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
async def me(user: User = Depends(get_current_active_user)):
    return user
