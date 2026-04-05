import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.models import FinancialRecord, RolePermission, User, UserRole  # noqa: F401

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finance.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def seed_role_permissions_session(session: Session) -> None:
    """Insert policy rows if empty (idempotent)."""
    from sqlmodel import select

    actions_by_role: dict[str, list[str]] = {
        UserRole.viewer.value: [
            "view_records",
            "view_dashboard",
        ],
        UserRole.analyst.value: [
            "view_records",
            "view_dashboard",
            "create_records",
            "update_records",
            "delete_records",
        ],
        UserRole.admin.value: [
            "view_records",
            "view_dashboard",
            "create_records",
            "update_records",
            "delete_records",
            "manage_users",
        ],
    }
    existing = session.exec(select(RolePermission)).first()
    if existing:
        return
    for role, actions in actions_by_role.items():
        for action in actions:
            session.add(RolePermission(role=role, action=action))
    session.commit()


def seed_role_permissions() -> None:
    with Session(engine) as session:
        seed_role_permissions_session(session)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
