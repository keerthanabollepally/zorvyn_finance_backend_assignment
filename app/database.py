import os
from collections.abc import Generator
from urllib.parse import urlparse, urlunparse

from sqlmodel import Session, SQLModel, create_engine

from app.models import FinancialRecord, RolePermission, User, UserRole  # noqa: F401


def _normalize_database_url(url: str) -> str:
    """Render/Heroku sometimes use postgres://; SQLAlchemy expects postgresql://."""
    if url.startswith("postgres://"):
        return "postgresql://" + url.removeprefix("postgres://")
    return url


def _add_sslmode_require_if_needed(url: str) -> str:
    """Managed Postgres (e.g. Render) often requires SSL for external connections."""
    if not url.startswith("postgresql"):
        return url
    parsed = urlparse(url)
    q = parsed.query
    if "sslmode=" in q or parsed.hostname in (None, "localhost", "127.0.0.1"):
        return url
    if os.getenv("DATABASE_SSL_REQUIRE", "").lower() in ("1", "true", "yes"):
        sep = "&" if q else ""
        new_query = f"{q}{sep}sslmode=require" if q else "sslmode=require"
        return urlunparse(parsed._replace(query=new_query))
    return url


_raw_url = os.getenv("DATABASE_URL", "sqlite:///./finance.db")
DATABASE_URL = _add_sslmode_require_if_needed(_normalize_database_url(_raw_url))

_connect_args: dict = {}
_engine_kwargs: dict = {"echo": False}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    **_engine_kwargs,
)


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
