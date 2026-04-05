"""Dashboard aggregations in SQL (not in-memory Python loops)."""

from datetime import date

from sqlalchemy import case, func
from sqlmodel import Session, select

from app.models import FinancialRecord, RecordType, User, UserRole


def _conditions(
    actor: User,
    *,
    user_id: int | None,
    date_from: date | None,
    date_to: date | None,
):
    conds = [FinancialRecord.is_deleted == False]  # noqa: E712
    if actor.role == UserRole.viewer:
        # Viewers are always scoped to their own records (ignore user_id query).
        conds.append(FinancialRecord.user_id == actor.id)
    elif actor.role == UserRole.analyst:
        if user_id is not None:
            conds.append(FinancialRecord.user_id == user_id)
    elif actor.role == UserRole.admin:
        if user_id is not None:
            conds.append(FinancialRecord.user_id == user_id)
    if date_from is not None:
        conds.append(FinancialRecord.date >= date_from)
    if date_to is not None:
        conds.append(FinancialRecord.date <= date_to)
    return conds


def compute_totals_sql(session: Session, actor: User, *, user_id: int | None = None) -> tuple[float, float]:
    """Return (total_income, total_expense) for net_balance tests and dashboard."""
    conds = _conditions(actor, user_id=user_id, date_from=None, date_to=None)
    income_case = case((FinancialRecord.type == RecordType.income, FinancialRecord.amount), else_=0)
    expense_case = case((FinancialRecord.type == RecordType.expense, FinancialRecord.amount), else_=0)
    stmt = select(
        func.coalesce(func.sum(income_case), 0.0),
        func.coalesce(func.sum(expense_case), 0.0),
    ).where(*conds)
    row = session.exec(stmt).one()
    return float(row[0]), float(row[1])


def net_balance_from_totals(total_income: float, total_expense: float) -> float:
    return total_income - total_expense


def summary(
    session: Session,
    actor: User,
    *,
    user_id: int | None = None,
    recent_limit: int = 10,
):
    total_income, total_expense = compute_totals_sql(session, actor, user_id=user_id)
    net = net_balance_from_totals(total_income, total_expense)
    conds = _conditions(actor, user_id=user_id, date_from=None, date_to=None)
    recent_stmt = (
        select(FinancialRecord)
        .where(*conds)
        .order_by(FinancialRecord.created_at.desc())
        .limit(recent_limit)
    )
    recent = list(session.exec(recent_stmt).all())
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net,
        "recent_activity": recent,
    }


def category_summary(session: Session, actor: User, *, user_id: int | None = None):
    conds = _conditions(actor, user_id=user_id, date_from=None, date_to=None)
    income_sum = func.coalesce(
        func.sum(case((FinancialRecord.type == RecordType.income, FinancialRecord.amount), else_=0)),
        0.0,
    )
    expense_sum = func.coalesce(
        func.sum(case((FinancialRecord.type == RecordType.expense, FinancialRecord.amount), else_=0)),
        0.0,
    )
    stmt = (
        select(FinancialRecord.category, income_sum, expense_sum)
        .where(*conds)
        .group_by(FinancialRecord.category)
        .order_by(FinancialRecord.category)
    )
    rows = session.exec(stmt).all()
    # total_amount = net flow per category (income - expense), per spec single number
    return [
        {
            "category": r[0],
            "total_amount": float(r[1]) - float(r[2]),
        }
        for r in rows
    ]


def _trend_date_group(session: Session, granularity: str):
    """SQLite uses strftime; PostgreSQL (e.g. Render) uses to_char."""
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        if granularity == "month":
            return func.to_char(FinancialRecord.date, "YYYY-MM")
        return func.to_char(FinancialRecord.date, 'IYYY-"W"IW')
    if granularity == "month":
        return func.strftime("%Y-%m", FinancialRecord.date)
    return func.strftime("%Y-W%W", FinancialRecord.date)


def trend(session: Session, actor: User, granularity: str, *, user_id: int | None = None):
    conds = _conditions(actor, user_id=user_id, date_from=None, date_to=None)
    date_group = _trend_date_group(session, granularity)
    income_sum = func.coalesce(
        func.sum(case((FinancialRecord.type == RecordType.income, FinancialRecord.amount), else_=0)),
        0.0,
    )
    expense_sum = func.coalesce(
        func.sum(case((FinancialRecord.type == RecordType.expense, FinancialRecord.amount), else_=0)),
        0.0,
    )
    stmt = (
        select(date_group, income_sum, expense_sum)
        .where(*conds)
        .group_by(date_group)
        .order_by(date_group)
    )
    rows = session.exec(stmt).all()
    return [
        {"date_group": str(r[0]), "income": float(r[1]), "expense": float(r[2])}
        for r in rows
    ]
