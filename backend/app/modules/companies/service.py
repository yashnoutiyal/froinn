"""Use cases for safe, atomic Super Admin company provisioning."""

import secrets
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.companies.models import (
    AmcContract,
    AmcPlan,
    AuditLog,
    Company,
    ModuleCatalog,
    NotificationOutbox,
    PlanModule,
    Role,
    Tenant,
    TenantModule,
    TenantStatus,
    User,
)
from app.modules.companies.schemas import (
    AmcInput,
    CompanyDetail,
    CompanyListItem,
    CompanyListResponse,
    CompanyPatch,
    CreateCompanyRequest,
    ModuleResponse,
    PageMeta,
    PlanResponse,
    ProvisionCompanyResponse,
)

DEFAULT_ROLES = (
    ("company_admin", "Company Admin", "Full control within this company."),
    ("operations_manager", "Operations Manager", "Orders, shipments, trips and dispatch."),
    ("dispatcher", "Dispatcher", "Trip assignment and dispatch operations."),
    ("accountant", "Accountant", "Invoices, payments and expenses."),
    ("warehouse_staff", "Warehouse Staff", "Inward, outward and storage operations."),
    ("driver", "Driver", "Assigned trips and POD upload."),
    ("customer", "Customer", "Own shipment tracking access."),
)

DEFAULT_MODULES = (
    ("dashboard", "Dashboard", "Core", "Tenant dashboard"),
    ("customers", "Customers", "Core", "Customer management"),
    ("orders", "Orders", "Core", "Order management"),
    ("users_roles", "Users & Roles", "Core", "Users and roles"),
    ("vehicles", "Vehicles", "Fleet", "Vehicle management"),
    ("drivers", "Drivers", "Fleet", "Driver management"),
    ("maintenance", "Maintenance", "Fleet", "Vehicle maintenance"),
    ("fuel", "Fuel", "Fleet", "Fuel management"),
    ("trips", "Trips", "Operations", "Trip operations"),
    ("dispatch", "Dispatch", "Operations", "Dispatch operations"),
    ("pod", "POD", "Operations", "Proof of delivery"),
    ("warehouse", "Warehouse", "Operations", "Warehouse operations"),
    ("gps_tracking", "GPS Tracking", "Tracking", "GPS tracking"),
    ("live_map", "Live Map", "Tracking", "Live location map"),
    ("billing", "Billing", "Finance", "Billing"),
    ("invoices", "Invoices", "Finance", "Invoice management"),
    ("expenses", "Expenses", "Finance", "Expense management"),
    ("analytics", "Analytics", "Advanced", "Analytics"),
    ("api_access", "API Access", "Advanced", "External API access"),
)

PLAN_MODULE_KEYS = {
    "BASIC": {"dashboard", "customers", "orders", "users_roles"},
    "PROFESSIONAL": {
        "dashboard",
        "customers",
        "orders",
        "users_roles",
        "vehicles",
        "drivers",
        "trips",
        "dispatch",
        "pod",
        "billing",
        "invoices",
        "gps_tracking",
    },
    "ENTERPRISE": {item[0] for item in DEFAULT_MODULES},
    "CUSTOM": set(),
}


class ProvisioningError(ValueError):
    pass


async def seed_catalogs(session: AsyncSession) -> None:
    """Idempotently seed the controlled module and plan catalog."""
    existing_modules = set((await session.scalars(select(ModuleCatalog.key))).all())
    for key, name, category, description in DEFAULT_MODULES:
        if key not in existing_modules:
            session.add(
                ModuleCatalog(key=key, name=name, category=category, description=description)
            )
    await session.flush()

    existing_plans = set((await session.scalars(select(AmcPlan.code))).all())
    for code, name, amount, custom in (
        ("BASIC", "Basic", 0, False),
        ("PROFESSIONAL", "Professional", 0, False),
        ("ENTERPRISE", "Enterprise", 0, False),
        ("CUSTOM", "Custom", None, True),
    ):
        if code not in existing_plans:
            session.add(AmcPlan(code=code, name=name, annual_amount=amount, is_custom=custom))
    await session.flush()

    modules = {
        module.key: module for module in (await session.scalars(select(ModuleCatalog))).all()
    }
    plans = {plan.code: plan for plan in (await session.scalars(select(AmcPlan))).all()}
    existing_links = set(
        (await session.execute(select(PlanModule.plan_id, PlanModule.module_id))).all()
    )
    for plan_code, keys in PLAN_MODULE_KEYS.items():
        for key in keys:
            link = (plans[plan_code].id, modules[key].id)
            if link not in existing_links:
                session.add(PlanModule(plan_id=link[0], module_id=link[1]))


async def list_plans(session: AsyncSession) -> list[PlanResponse]:
    plans = (
        await session.scalars(
            select(AmcPlan).where(AmcPlan.is_active.is_(True)).order_by(AmcPlan.name)
        )
    ).all()
    links = (
        await session.execute(select(PlanModule.plan_id, ModuleCatalog.key).join(ModuleCatalog))
    ).all()
    key_map: dict[UUID, list[str]] = {}
    for plan_id, key in links:
        key_map.setdefault(plan_id, []).append(key)
    return [
        PlanResponse(
            code=p.code,
            name=p.name,
            annual_amount=p.annual_amount,
            is_custom=p.is_custom,
            module_keys=sorted(key_map.get(p.id, [])),
        )
        for p in plans
    ]


async def list_modules(session: AsyncSession) -> list[ModuleResponse]:
    modules = (
        await session.scalars(
            select(ModuleCatalog)
            .where(ModuleCatalog.is_active.is_(True))
            .order_by(ModuleCatalog.category, ModuleCatalog.name)
        )
    ).all()
    return [
        ModuleResponse(key=m.key, name=m.name, category=m.category, description=m.description)
        for m in modules
    ]


async def provision_company(
    session: AsyncSession, request: CreateCompanyRequest, actor_id: UUID
) -> ProvisionCompanyResponse:
    plan = await session.scalar(
        select(AmcPlan).where(
            AmcPlan.code == request.amc.plan_code.upper(), AmcPlan.is_active.is_(True)
        )
    )
    if plan is None:
        raise ProvisioningError("The selected AMC plan does not exist or is inactive.")
    if await session.scalar(select(Company.id).where(Company.email == str(request.company.email))):
        raise ProvisioningError("A company with this email already exists.")
    if await session.scalar(select(User.id).where(User.email == str(request.primary_admin.email))):
        raise ProvisioningError("A user with the primary admin email already exists.")

    catalog = {
        m.key: m
        for m in (
            await session.scalars(select(ModuleCatalog).where(ModuleCatalog.is_active.is_(True)))
        ).all()
    }
    plan_keys = set(
        (
            await session.scalars(
                select(ModuleCatalog.key).join(PlanModule).where(PlanModule.plan_id == plan.id)
            )
        ).all()
    )
    selected_keys = plan_keys | {key.lower() for key in request.module_keys}
    unknown = selected_keys - catalog.keys()
    if unknown:
        raise ProvisioningError(f"Unknown or inactive module keys: {', '.join(sorted(unknown))}.")

    tenant = Tenant(code=f"TEN-{uuid4().hex[:8].upper()}")
    session.add(tenant)
    await session.flush()
    company_data = request.company.model_dump(mode="json")
    company_data["website"] = str(company_data["website"]) if company_data.get("website") else None
    company = Company(tenant_id=tenant.id, **company_data)
    session.add(company)
    for module_key in selected_keys:
        session.add(TenantModule(tenant_id=tenant.id, module_id=catalog[module_key].id))
    for code, name, description in DEFAULT_ROLES:
        session.add(
            Role(tenant_id=tenant.id, code=code, name=name, description=description, is_system=True)
        )
    await session.flush()
    company_admin_role = await session.scalar(
        select(Role).where(Role.tenant_id == tenant.id, Role.code == "company_admin")
    )
    generated_password = None
    password = request.primary_admin.password
    if password is None:
        generated_password = secrets.token_urlsafe(18)
        password = generated_password
    admin = User(
        tenant_id=tenant.id,
        role_id=company_admin_role.id,
        full_name=request.primary_admin.full_name,
        email=str(request.primary_admin.email),
        phone=request.primary_admin.phone,
        password_hash=hash_password(password),
    )
    session.add(admin)
    contract = AmcContract(
        tenant_id=tenant.id, plan_id=plan.id, **request.amc.model_dump(exclude={"plan_code"})
    )
    session.add(contract)
    if request.primary_admin.send_welcome_email:
        session.add(
            NotificationOutbox(
                tenant_id=tenant.id,
                event_type="company_admin_welcome",
                recipient_email=admin.email,
                payload={"company_name": company.name, "user_id": str(admin.id)},
            )
        )
    session.add(
        AuditLog(
            tenant_id=tenant.id,
            actor_user_id=actor_id,
            action="company.provisioned",
            entity_type="company",
            entity_id=company.id,
            metadata_={
                "tenant_code": tenant.code,
                "plan_code": plan.code,
                "module_keys": sorted(selected_keys),
            },
        )
    )
    await session.flush()
    detail = await get_company_detail(session, company.id)
    return ProvisionCompanyResponse(
        company=detail,
        primary_admin_user_id=admin.id,
        invitation_queued=request.primary_admin.send_welcome_email,
        generated_password=generated_password,
    )


async def get_company_detail(session: AsyncSession, company_id: UUID) -> CompanyDetail:
    row = (
        await session.execute(select(Company, Tenant).join(Tenant).where(Company.id == company_id))
    ).one_or_none()
    if row is None:
        raise ProvisioningError("Company not found.")
    company, tenant = row
    contract = await session.scalar(
        select(AmcContract).where(
            AmcContract.tenant_id == tenant.id, AmcContract.is_current.is_(True)
        )
    )
    plan = await session.get(AmcPlan, contract.plan_id) if contract else None
    enabled = (
        (
            await session.execute(
                select(ModuleCatalog)
                .join(TenantModule)
                .where(TenantModule.tenant_id == tenant.id, TenantModule.enabled.is_(True))
                .order_by(ModuleCatalog.category, ModuleCatalog.name)
            )
        )
        .scalars()
        .all()
    )
    amc = (
        AmcInput(
            plan_code=plan.code,
            start_date=contract.start_date,
            end_date=contract.end_date,
            amount=contract.amount,
            payment_status=contract.payment_status,
            grace_period_days=contract.grace_period_days,
            auto_renew=contract.auto_renew,
            notes=contract.notes,
        )
        if contract and plan
        else None
    )
    return CompanyDetail(
        id=company.id,
        tenant_id=tenant.id,
        tenant_code=tenant.code,
        name=company.name,
        email=company.email,
        plan_code=plan.code if plan else None,
        amc_end_date=contract.end_date if contract else None,
        status=tenant.status,
        created_at=company.created_at,
        company_type=company.company_type,
        gst_number=company.gst_number,
        pan_number=company.pan_number,
        address_line=company.address_line,
        city=company.city,
        state=company.state,
        country=company.country,
        pincode=company.pincode,
        phone=company.phone,
        website=company.website,
        logo_object_key=company.logo_object_key,
        modules=[
            ModuleResponse(key=m.key, name=m.name, category=m.category, description=m.description)
            for m in enabled
        ],
        amc=amc,
    )


async def list_companies(
    session: AsyncSession,
    page: int,
    page_size: int,
    search: str | None,
    status: TenantStatus | None,
) -> CompanyListResponse:
    query = (
        select(Company, Tenant, AmcContract, AmcPlan)
        .join(Tenant)
        .outerjoin(
            AmcContract, (AmcContract.tenant_id == Tenant.id) & AmcContract.is_current.is_(True)
        )
        .outerjoin(AmcPlan, AmcPlan.id == AmcContract.plan_id)
    )
    if search:
        query = query.where(Company.name.ilike(f"%{search}%"))
    if status:
        query = query.where(Tenant.status == status)
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0
    rows = (
        await session.execute(
            query.order_by(Company.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return CompanyListResponse(
        items=[
            CompanyListItem(
                id=c.id,
                tenant_id=t.id,
                tenant_code=t.code,
                name=c.name,
                email=c.email,
                plan_code=p.code if p else None,
                amc_end_date=a.end_date if a else None,
                status=t.status,
                created_at=c.created_at,
            )
            for c, t, a, p in rows
        ],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


async def update_company(
    session: AsyncSession, company_id: UUID, patch: CompanyPatch, actor_id: UUID
) -> CompanyDetail:
    company = await session.get(Company, company_id)
    if company is None:
        raise ProvisioningError("Company not found.")
    for field, value in patch.model_dump(exclude_unset=True, mode="json").items():
        setattr(company, field, str(value) if field == "website" and value else value)
    session.add(
        AuditLog(
            tenant_id=company.tenant_id,
            actor_user_id=actor_id,
            action="company.updated",
            entity_type="company",
            entity_id=company.id,
            metadata_={"fields": sorted(patch.model_fields_set)},
        )
    )
    await session.flush()
    return await get_company_detail(session, company_id)


async def replace_modules(
    session: AsyncSession, company_id: UUID, keys: set[str], actor_id: UUID
) -> CompanyDetail:
    company = await session.get(Company, company_id)
    if company is None:
        raise ProvisioningError("Company not found.")
    catalog = {
        m.key: m
        for m in (
            await session.scalars(select(ModuleCatalog).where(ModuleCatalog.is_active.is_(True)))
        ).all()
    }
    normalized = {key.lower() for key in keys}
    if normalized - catalog.keys():
        raise ProvisioningError(
            f"Unknown module keys: {', '.join(sorted(normalized - catalog.keys()))}."
        )
    await session.execute(
        update(TenantModule)
        .where(TenantModule.tenant_id == company.tenant_id)
        .values(enabled=False)
    )
    existing = {
        row.module_id: row
        for row in (
            await session.scalars(
                select(TenantModule).where(TenantModule.tenant_id == company.tenant_id)
            )
        ).all()
    }
    for key in normalized:
        item = existing.get(catalog[key].id)
        if item:
            item.enabled = True
        else:
            session.add(
                TenantModule(tenant_id=company.tenant_id, module_id=catalog[key].id, enabled=True)
            )
    session.add(
        AuditLog(
            tenant_id=company.tenant_id,
            actor_user_id=actor_id,
            action="company.modules_replaced",
            entity_type="company",
            entity_id=company.id,
            metadata_={"module_keys": sorted(normalized)},
        )
    )
    await session.flush()
    return await get_company_detail(session, company_id)


async def set_status(
    session: AsyncSession,
    company_id: UUID,
    status: TenantStatus,
    reason: str | None,
    actor_id: UUID,
) -> CompanyDetail:
    company = await session.get(Company, company_id)
    if company is None:
        raise ProvisioningError("Company not found.")
    tenant = await session.get(Tenant, company.tenant_id)
    tenant.status, tenant.suspension_reason = status, reason
    tenant.suspended_at = datetime.now(UTC) if status == TenantStatus.SUSPENDED else None
    session.add(
        AuditLog(
            tenant_id=tenant.id,
            actor_user_id=actor_id,
            action=f"company.{status}",
            entity_type="company",
            entity_id=company.id,
            metadata_={"reason": reason} if reason else {},
        )
    )
    await session.flush()
    return await get_company_detail(session, company_id)


async def renew_amc(
    session: AsyncSession, company_id: UUID, renewal: AmcInput, actor_id: UUID
) -> CompanyDetail:
    company = await session.get(Company, company_id)
    if company is None:
        raise ProvisioningError("Company not found.")
    plan = await session.scalar(
        select(AmcPlan).where(
            AmcPlan.code == renewal.plan_code.upper(), AmcPlan.is_active.is_(True)
        )
    )
    if plan is None:
        raise ProvisioningError("The selected AMC plan does not exist or is inactive.")
    await session.execute(
        update(AmcContract)
        .where(AmcContract.tenant_id == company.tenant_id, AmcContract.is_current.is_(True))
        .values(is_current=False)
    )
    session.add(
        AmcContract(
            tenant_id=company.tenant_id,
            plan_id=plan.id,
            **renewal.model_dump(exclude={"plan_code"}),
        )
    )
    session.add(
        AuditLog(
            tenant_id=company.tenant_id,
            actor_user_id=actor_id,
            action="amc.renewed",
            entity_type="company",
            entity_id=company.id,
            metadata_={"plan_code": plan.code},
        )
    )
    await session.flush()
    return await get_company_detail(session, company_id)
