from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from ai_surveillance_system.db.models import User, UserRole
from ai_surveillance_system.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class AuthService:

    async def register(
        self,
        email: str,
        password: str,
        full_name: str | None,
        db: AsyncSession,
        role: UserRole = UserRole.OPERATOR,
    ) -> User:
        # Check uniqueness
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info(f"User registered: {email} (role={role})")
        return user

    async def authenticate(
        self, email: str, password: str, db: AsyncSession
    ) -> User:
        """
        Verifies credentials and returns the user.
        """
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)
        await db.flush()
        return user

    def issue_tokens(self, user: User) -> dict:
        """
        Issues a fresh access and refresh token pair for a user.
        """
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def get_user_by_id(self, user_id: str, db: AsyncSession) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def refresh_access_token(
        self, refresh_token: str, db: AsyncSession
    ) -> dict:
        """
        Validates a refresh token and issues a new access token.
        """
        from jose import jwt
        try:
            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[
                    settings.ALGORITHM]
            )
            if payload.get("type") != "refresh":
                raise ValueError("Not a refresh token")
            user_id = payload.get("sub")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user = await self.get_user_by_id(user_id, db)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return self.issue_tokens(user)


auth_service = AuthService()
