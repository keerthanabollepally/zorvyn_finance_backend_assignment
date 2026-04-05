from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    viewer = "viewer"
    analyst = "analyst"
    admin = "admin"


class RecordType(str, Enum):
    income = "income"
    expense = "expense"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    hashed_password: str
    role: UserRole = Field(default=UserRole.viewer)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FinancialRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    amount: float
    type: RecordType
    category: str = Field(index=True)
    date: date
    notes: Optional[str] = None
    is_deleted: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RolePermission(SQLModel, table=True):
    """Maps a role to an allowed action (policy-style RBAC)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    role: str = Field(index=True)
    action: str = Field(index=True)
