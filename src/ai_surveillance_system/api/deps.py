from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.core.security import decode_token
from ai_surveillance_system.db.session import get_db
from ai_surveillance_system.db.models import User, UserRole
from ai_surveillance_system.services.auth_service import auth_service

# HTTPBearer extracts the token from Authorization: Bearer <token>
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Core auth dependency - inject into any route that requires authentication.
    """
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")

    user = await auth_service.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Alias — explicit name for readability in routes
    """
    return user


def require_role(*roles: UserRole):
    """
    Role-based access control (RBAC) dependency factory
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {[r.value for r in roles]}",
            )
        return user
    return role_checker
