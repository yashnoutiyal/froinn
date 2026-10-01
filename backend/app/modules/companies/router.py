from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import Principal, require_super_admin
from app.modules.companies.models import TenantStatus
from app.modules.companies.schemas import (
    AmcInput,
    CompanyDetail,
    CompanyListResponse,
    CompanyPatch,
    CreateCompanyRequest,
    ModuleResponse,
    ModuleSelection,
    PlanResponse,
    ProvisionCompanyResponse,
    SuspensionRequest,
)
from app.modules.companies.service import (
    ProvisioningError,
    get_company_detail,
    list_companies,
    list_modules,
    list_plans,
    provision_company,
    renew_amc,
    replace_modules,
    set_status,
    update_company,
)

router = APIRouter(prefix="/admin", tags=["Super Admin · Companies"])


def translate_error(error: ProvisioningError) -> HTTPException:
    message = str(error)
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND
        if message == "Company not found."
        else status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=message,
    )


@router.get("/catalog/modules", response_model=list[ModuleResponse], summary="List module catalog")
async def get_module_catalog(
    _: Principal = Depends(require_super_admin), session: AsyncSession = Depends(get_db_session)
) -> list[ModuleResponse]:
    """Load the module checkboxes for the company provisioning wizard."""
    return await list_modules(session)


@router.get(
    "/catalog/plans",
    response_model=list[PlanResponse],
    summary="List AMC plans with included modules",
)
async def get_plans(
    _: Principal = Depends(require_super_admin), session: AsyncSession = Depends(get_db_session)
) -> list[PlanResponse]:
    return await list_plans(session)


@router.get("/companies", response_model=CompanyListResponse, summary="List companies")
async def get_companies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    company_status: TenantStatus | None = Query(default=None, alias="status"),
    _: Principal = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyListResponse:
    """Paginated data for the Super Admin company list screen."""
    return await list_companies(session, page, page_size, search, company_status)


@router.post(
    "/companies",
    response_model=ProvisionCompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a company",
    responses={
        401: {"description": "Unauthenticated"},
        403: {"description": "Not a Super Admin"},
        422: {"description": "Invalid plan, module, or duplicate email"},
    },
)
async def create_company(
    payload: CreateCompanyRequest,
    principal: Principal = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ProvisionCompanyResponse:
    """Atomically creates tenant, company, roles, entitlements, AMC, admin and welcome-email outbox entry."""
    try:
        return await provision_company(session, payload, principal.user_id)
    except ProvisioningError as error:
        raise translate_error(error)


@router.get("/companies/{company_id}", response_model=CompanyDetail, summary="Get company details")
async def get_company(
    company_id: UUID,
    _: Principal = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetail:
    try:
        return await get_company_detail(session, company_id)
    except ProvisioningError as error:
        raise translate_error(error)


@router.patch(
    "/companies/{company_id}", response_model=CompanyDetail, summary="Update company profile"
)
async def patch_company(
    company_id: UUID,
    payload: CompanyPatch,
    principal: Principal = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetail:
    try:
        return await update_company(session, company_id, payload, principal.user_id)
    except ProvisioningError as error:
        raise translate_error(error)


@router.put(
    "/companies/{company_id}/modules",
    response_model=CompanyDetail,
    summary="Replace enabled modules",
)
async def put_modules(
    company_id: UUID,
    payload: ModuleSelection,
    principal: Principal = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetail:
    """Replaces entitlements. The frontend should refresh menus after a successful call."""
    try:
        return await replace_modules(session, company_id, payload.module_keys, principal.user_id)
    except ProvisioningError as error:
        raise translate_error(error)


@router.post(
    "/companies/{company_id}/amc/renewals",
    response_model=CompanyDetail,
    summary="Renew or replace current AMC",
)
async def post_renewal(
    company_id: UUID,
    payload: AmcInput,
    principal: Principal = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetail:
    try:
        return await renew_amc(session, company_id, payload, principal.user_id)
    except ProvisioningError as error:
        raise translate_error(error)


@router.post(
    "/companies/{company_id}/suspend",
    response_model=CompanyDetail,
    summary="Suspend company access",
)
async def suspend_company(
    company_id: UUID,
    payload: SuspensionRequest,
    principal: Principal = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetail:
    """Suspends access without deleting tenant data."""
    try:
        return await set_status(
            session, company_id, TenantStatus.SUSPENDED, payload.reason, principal.user_id
        )
    except ProvisioningError as error:
        raise translate_error(error)


@router.post(
    "/companies/{company_id}/restore",
    response_model=CompanyDetail,
    summary="Restore suspended company access",
)
async def restore_company(
    company_id: UUID,
    principal: Principal = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetail:
    try:
        return await set_status(session, company_id, TenantStatus.ACTIVE, None, principal.user_id)
    except ProvisioningError as error:
        raise translate_error(error)
