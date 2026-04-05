import os

os.environ["FINANCE_SKIP_DB_INIT"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.auth import hash_password
from app.database import get_session, seed_role_permissions_session
from app.main import app
from app.models import FinancialRecord, RecordType, User, UserRole


@pytest.fixture(name="engine")
def engine_fixture():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        seed_role_permissions_session(s)
    yield eng
    SQLModel.metadata.drop_all(eng)


@pytest.fixture(name="client")
def client_fixture(engine):
    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(session: Session, *, email: str, role: UserRole = UserRole.viewer) -> User:
    u = User(
        email=email,
        name="Test User",
        hashed_password=hash_password("password123"),
        role=role,
        is_active=True,
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


@pytest.fixture
def admin_user(engine):
    with Session(engine) as s:
        return make_user(s, email="admin@test.com", role=UserRole.admin)


@pytest.fixture
def viewer_user(engine):
    with Session(engine) as s:
        return make_user(s, email="viewer@test.com", role=UserRole.viewer)


@pytest.fixture
def analyst_user(engine):
    with Session(engine) as s:
        return make_user(s, email="analyst@test.com", role=UserRole.analyst)


def login(client: TestClient, email: str, password: str = "password123") -> str:
    r = client.post("/users/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(admin_user, client):
    token = login(client, admin_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(viewer_user, client):
    token = login(client, viewer_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def analyst_headers(analyst_user, client):
    token = login(client, analyst_user.email)
    return {"Authorization": f"Bearer {token}"}
