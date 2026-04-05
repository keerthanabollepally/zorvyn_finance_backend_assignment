from datetime import date

from sqlmodel import Session

from app.models import FinancialRecord, RecordType


def test_dashboard_summary_net(client, analyst_headers, engine, analyst_user):
    with Session(engine) as s:
        s.add(
            FinancialRecord(
                user_id=analyst_user.id,
                amount=300,
                type=RecordType.income,
                category="a",
                date=date(2024, 1, 1),
            )
        )
        s.add(
            FinancialRecord(
                user_id=analyst_user.id,
                amount=100,
                type=RecordType.expense,
                category="b",
                date=date(2024, 1, 2),
            )
        )
        s.commit()

    r = client.get("/dashboard/summary", headers=analyst_headers)
    assert r.status_code == 200
    j = r.json()
    assert j["total_income"] >= 300
    assert j["total_expense"] >= 100
    assert j["net_balance"] == j["total_income"] - j["total_expense"]
    assert isinstance(j["recent_activity"], list)


def test_category_summary_and_trend(client, analyst_headers, engine, analyst_user):
    with Session(engine) as s:
        s.add(
            FinancialRecord(
                user_id=analyst_user.id,
                amount=50,
                type=RecordType.expense,
                category="food",
                date=date(2024, 6, 10),
            )
        )
        s.commit()

    r = client.get("/dashboard/category-summary", headers=analyst_headers)
    assert r.status_code == 200
    cats = {x["category"]: x["total_amount"] for x in r.json()}
    assert "food" in cats

    r = client.get("/dashboard/trend?granularity=month", headers=analyst_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
