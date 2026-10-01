from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.modules.companies.models import Permission, RolePermission, Tenant, TenantStatus, User

bearer_scheme = HTTPBearer(auto_error=False)
password_hash = PasswordHash.recommended()


@dataclass(frozen=True)
class Principal:
    """Authenticated identity shape used by authorization dependencies."""

    user_id: UUID
    tenant_ids: frozenset[UUID]
    permissions: frozenset[str]
    is_super_admin: bool = False


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, password_hash_value: str) -> bool:
    return password_hash.verify(password, password_hash_value)


def create_access_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> Principal:
    """Validate bearer token and load current authorization state from the database."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret,
            algorithms=[get_settings().jwt_algorithm],
        )
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    if user.tenant_id is not None:
        tenant_status = await session.scalar(
            select(Tenant.status).join(User, User.tenant_id == Tenant.id).where(User.id == user.id)
        )
        if tenant_status == TenantStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This company account is suspended."
            )
    permissions: set[str] = set()
    if user.role_id:
        permissions = set(
            (
                await session.scalars(
                    select(Permission.code)
                    .join(RolePermission)
                    .where(RolePermission.role_id == user.role_id)
                )
            ).all()
        )
    return Principal(
        user_id=user.id,
        tenant_ids=frozenset({user.tenant_id}) if user.tenant_id else frozenset(),
        permissions=frozenset(permissions),
        is_super_admin=user.is_super_admin,
    )


async def require_super_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if not principal.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access is required."
        )
    return principal
