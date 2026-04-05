from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import RecordType, UserRole


class ErrorResponse(BaseModel):
    error: str
    message: str
    status_code: int


# --- Users ---
class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=200)
    role: Optional[UserRole] = None

    @field_validator("role")
    @classmethod
    def default_role(cls, v: Optional[UserRole]) -> UserRole:
        return v if v is not None else UserRole.viewer


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdateAdmin(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# --- Records ---
class FinancialRecordCreate(BaseModel):
    amount: float = Field(gt=0)
    type: RecordType
    category: str = Field(min_length=1, max_length=120)
    date: date
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if v is None:
            return v
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format.")
        return v


class FinancialRecordUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    type: Optional[RecordType] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=120)
    date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format.")
        return v


class FinancialRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount: float
    type: RecordType
    category: str
    date: date
    notes: Optional[str]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# --- Dashboard ---
class DashboardSummaryOut(BaseModel):
    total_income: float
    total_expense: float
    net_balance: float
    recent_activity: list[FinancialRecordOut]


class CategorySummaryItem(BaseModel):
    category: str
    total_amount: float


class TrendItem(BaseModel):
    date_group: str
    income: float
    expense: float
