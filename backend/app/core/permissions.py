from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.core.security import Principal, get_current_principal


def require_permission(permission: str) -> Callable:
    """Dependency factory for future RBAC and fine-grained permission checks."""

    async def check(principal: Principal = Depends(get_current_principal)) -> Principal:
        if permission not in principal.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
        return principal

    return check
