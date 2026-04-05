from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.database import get_session
from app.middleware.auth_middleware import RequirePermission
from app.models import RecordType, User, UserRole
from app.schemas import FinancialRecordCreate, FinancialRecordOut, FinancialRecordUpdate
from app.services import record_service

router = APIRouter(prefix="/records", tags=["records"])


@router.post("", response_model=FinancialRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(
    body: FinancialRecordCreate,
    user: Annotated[User, Depends(RequirePermission("create_records"))],
    session: Annotated[Session, Depends(get_session)],
):
    return record_service.create_record(
        session,
        user,
        amount=body.amount,
        type_=body.type,
        category=body.category,
        d=body.date,
        notes=body.notes,
    )


@router.get("")
def list_records(
    user: Annotated[User, Depends(RequirePermission("view_records"))],
    session: Annotated[Session, Depends(get_session)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    type: Optional[RecordType] = Query(None, alias="type"),
    category: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None, description="Filter by owner (admin/analyst)"),
    q: Optional[str] = Query(None, description="Search notes or category (substring)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_deleted: bool = Query(False, description="Admin only: include soft-deleted rows"),
):
    if include_deleted and user.role != UserRole.admin:
        include_deleted = False
    rows, total = record_service.list_records(
        session,
        user,
        date_from=date_from,
        date_to=date_to,
        type_=type,
        category=category,
        user_id=user_id,
        q=q,
        offset=offset,
        limit=limit,
        include_deleted=include_deleted,
    )
    return {
        "items": rows,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{record_id}", response_model=FinancialRecordOut)
def get_record(
    record_id: int,
    user: Annotated[User, Depends(RequirePermission("view_records"))],
    session: Annotated[Session, Depends(get_session)],
):
    return record_service.get_record(session, user, record_id)


@router.patch("/{record_id}", response_model=FinancialRecordOut)
def patch_record(
    record_id: int,
    body: FinancialRecordUpdate,
    user: Annotated[User, Depends(RequirePermission("update_records"))],
    session: Annotated[Session, Depends(get_session)],
):
    return record_service.update_record(
        session,
        user,
        record_id,
        amount=body.amount,
        type_=body.type,
        category=body.category,
        d=body.date,
        notes=body.notes,
    )


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: int,
    user: Annotated[User, Depends(RequirePermission("delete_records"))],
    session: Annotated[Session, Depends(get_session)],
    hard: bool = Query(False, description="Admin only: permanently remove row"),
):
    if hard and user.role != UserRole.admin:
        hard = False
    record_service.delete_record(session, user, record_id, hard=hard)
    return None
