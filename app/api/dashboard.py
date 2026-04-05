from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database import get_session
from app.middleware.auth_middleware import RequirePermission
from app.models import User
from app.schemas import CategorySummaryItem, DashboardSummaryOut, FinancialRecordOut, TrendItem
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def dashboard_summary(
    user: Annotated[User, Depends(RequirePermission("view_dashboard"))],
    session: Annotated[Session, Depends(get_session)],
    user_id: Optional[int] = Query(None, description="Scope to user (admin/analyst)"),
):
    data = dashboard_service.summary(session, user, user_id=user_id)
    return DashboardSummaryOut(
        total_income=data["total_income"],
        total_expense=data["total_expense"],
        net_balance=data["net_balance"],
        recent_activity=[FinancialRecordOut.model_validate(r) for r in data["recent_activity"]],
    )


@router.get("/category-summary", response_model=list[CategorySummaryItem])
def category_summary(
    user: Annotated[User, Depends(RequirePermission("view_dashboard"))],
    session: Annotated[Session, Depends(get_session)],
    user_id: Optional[int] = Query(None),
):
    rows = dashboard_service.category_summary(session, user, user_id=user_id)
    return [CategorySummaryItem(**r) for r in rows]


@router.get("/trend", response_model=list[TrendItem])
def trend(
    user: Annotated[User, Depends(RequirePermission("view_dashboard"))],
    session: Annotated[Session, Depends(get_session)],
    granularity: str = Query("month", pattern="^(week|month)$"),
    user_id: Optional[int] = Query(None),
):
    rows = dashboard_service.trend(session, user, granularity, user_id=user_id)
    return [TrendItem(**r) for r in rows]
