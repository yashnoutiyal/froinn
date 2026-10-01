from contextvars import ContextVar
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.core.security import Principal, get_current_principal

_tenant_context: ContextVar[UUID | None] = ContextVar("tenant_context", default=None)


def current_tenant_id() -> UUID:
    tenant_id = _tenant_context.get()
    if tenant_id is None:
        raise RuntimeError("Tenant context has not been resolved for this request.")
    return tenant_id


async def get_authorized_tenant(
    principal: Principal = Depends(get_current_principal),
) -> UUID:
    """Resolve tenant from trusted auth state; never from a client tenant_id field."""
    if len(principal.tenant_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A single authorized tenant must be selected by the authentication layer.",
        )
    tenant_id = next(iter(principal.tenant_ids))
    _tenant_context.set(tenant_id)
    return tenant_id
