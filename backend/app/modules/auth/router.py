from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.security import Principal, create_access_token, get_current_principal, verify_password
from app.modules.auth.schemas import CurrentUserResponse, LoginRequest, TokenResponse
from app.modules.companies.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in",
    responses={401: {"description": "Invalid credentials"}},
)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == str(payload.email)))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        )
    user.last_login_at = datetime.now(UTC)
    return TokenResponse(
        access_token=create_access_token(user),
        expires_in=get_settings().jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=CurrentUserResponse, summary="Get current access context")
async def me(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUserResponse:
    user = await session.get(User, principal.user_id)
    return CurrentUserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        full_name=user.full_name,
        email=user.email,
        is_super_admin=user.is_super_admin,
        permissions=sorted(principal.permissions),
        last_login_at=user.last_login_at,
    )
