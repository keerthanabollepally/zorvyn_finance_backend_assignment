from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.exceptions import AppError
from app.models import RolePermission, User, UserRole


def check_permission(session: Session, user: User, action: str) -> bool:
    """Return True if the user's role is granted `action` in RolePermission (policy table)."""
    row = session.exec(
        select(RolePermission).where(
            RolePermission.role == user.role.value,
            RolePermission.action == action,
        )
    ).first()
    return row is not None


def require_role(*allowed: UserRole):
    """Dependency factory: allow only listed roles (in addition to active user)."""

    allowed_values = {r.value for r in allowed}

    def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role.value not in allowed_values:
            raise AppError(
                "forbidden",
                "This endpoint requires a different role.",
                status_code=403,
            )
        return user

    return _dep


class RequirePermission:
    """Depends(RequirePermission('view_records')) — policy check via RolePermission table."""

    def __init__(self, action: str) -> None:
        self.action = action

    def __call__(
        self,
        user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
    ) -> User:
        if not check_permission(session, user, self.action):
            raise AppError(
                "forbidden",
                f"Missing permission: {self.action}",
                status_code=403,
            )
        return user
