from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.modules.companies.models import PaymentStatus, TenantStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class CompanyDetailsInput(ApiModel):
    name: str = Field(min_length=2, max_length=200, examples=["ABC Logistics"])
    company_type: str = Field(min_length=2, max_length=80, examples=["Logistics"])
    gst_number: str | None = Field(default=None, pattern=r"^[0-9A-Z]{15}$")
    pan_number: str | None = Field(default=None, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]$")
    address_line: str = Field(min_length=5, max_length=2000)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str = Field(default="India", max_length=100)
    pincode: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr
    website: HttpUrl | None = None
    logo_object_key: str | None = Field(default=None, max_length=512)

    @field_validator("gst_number", "pan_number", mode="before")
    @classmethod
    def uppercase_tax_ids(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class AmcInput(ApiModel):
    plan_code: str = Field(examples=["PROFESSIONAL"])
    start_date: date
    end_date: date
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    payment_status: PaymentStatus = PaymentStatus.PENDING
    grace_period_days: int = Field(default=15, ge=0, le=365)
    auto_renew: bool = False
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def date_range_is_valid(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be later than start_date")
        return self


class PrimaryAdminInput(ApiModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    send_welcome_email: bool = True


class CreateCompanyRequest(ApiModel):
    company: CompanyDetailsInput
    module_keys: set[str] = Field(
        default_factory=set, description="Modules in addition to the selected plan."
    )
    amc: AmcInput
    primary_admin: PrimaryAdminInput


class CompanyPatch(ApiModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    company_type: str | None = Field(default=None, min_length=2, max_length=80)
    address_line: str | None = Field(default=None, min_length=5, max_length=2000)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    website: HttpUrl | None = None
    logo_object_key: str | None = Field(default=None, max_length=512)


class ModuleSelection(ApiModel):
    module_keys: set[str]


class SuspensionRequest(ApiModel):
    reason: str = Field(min_length=3, max_length=1000)


class ModuleResponse(ApiModel):
    key: str
    name: str
    category: str
    description: str | None
    enabled: bool = True


class PlanResponse(ApiModel):
    code: str
    name: str
    annual_amount: Decimal | None
    is_custom: bool
    module_keys: list[str]


class CompanyListItem(ApiModel):
    id: UUID
    tenant_id: UUID
    tenant_code: str
    name: str
    email: EmailStr
    plan_code: str | None
    amc_end_date: date | None
    status: TenantStatus
    created_at: datetime


class PageMeta(ApiModel):
    page: int
    page_size: int
    total: int


class CompanyListResponse(ApiModel):
    items: list[CompanyListItem]
    meta: PageMeta


class CompanyDetail(CompanyListItem):
    company_type: str
    gst_number: str | None
    pan_number: str | None
    address_line: str
    city: str | None
    state: str | None
    country: str
    pincode: str | None
    phone: str | None
    website: str | None
    logo_object_key: str | None
    modules: list[ModuleResponse]
    amc: AmcInput | None


class ProvisionCompanyResponse(ApiModel):
    company: CompanyDetail
    primary_admin_user_id: UUID
    invitation_queued: bool
    generated_password: str | None = Field(
        default=None,
        description="Returned only once when the request omits a password. Store it securely.",
    )
