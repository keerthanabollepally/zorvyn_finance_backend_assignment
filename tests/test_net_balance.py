"""Unit-style tests for dashboard totals (business logic + SQL)."""

from datetime import date

from sqlmodel import Session

from app.models import FinancialRecord, RecordType, User, UserRole
from app.services.dashboard_service import compute_totals_sql, net_balance_from_totals
from tests.conftest import make_user


def test_net_balance_from_totals_pure():
    assert net_balance_from_totals(500.0, 200.0) == 300.0


def test_compute_totals_sql(engine):
    with Session(engine) as s:
        u = make_user(s, email="nb@test.com", role=UserRole.analyst)
        s.add(
            FinancialRecord(
                user_id=u.id,
                amount=100,
                type=RecordType.income,
                category="i",
                date=date(2024, 1, 1),
            )
        )
        s.add(
            FinancialRecord(
                user_id=u.id,
                amount=40,
                type=RecordType.expense,
                category="e",
                date=date(2024, 1, 2),
            )
        )
        s.commit()
        inc, exp = compute_totals_sql(s, u, user_id=None)
        assert inc == 100.0
        assert exp == 40.0
        assert net_balance_from_totals(inc, exp) == 60.0
