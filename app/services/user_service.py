from datetime import datetime

from sqlmodel import Session, select

from app.auth import hash_password, verify_password
from app.exceptions import AppError
from app.models import User, UserRole
from app.schemas import UserSignup, UserUpdateAdmin


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()


def create_user(session: Session, data: UserSignup) -> User:
    if get_user_by_email(session, data.email):
        raise AppError("email_taken", "An account with this email already exists.", 400)
    # Public signup cannot self-assign elevated roles (documented in README).
    effective_role = UserRole.viewer
    if data.role is not None and data.role != UserRole.viewer:
        raise AppError(
            "invalid_role_signup",
            "New accounts must register as viewer. Contact an admin for role changes.",
            400,
        )
    now = datetime.utcnow()
    user = User(
        email=data.email,
        name=data.name,
        hashed_password=hash_password(data.password),
        role=effective_role,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, email: str, password: str) -> User:
    user = get_user_by_email(session, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise AppError("invalid_credentials", "Invalid email or password.", 401)
    if not user.is_active:
        raise AppError("account_disabled", "This account has been deactivated.", 403)
    return user


def list_users(session: Session) -> list[User]:
    return list(session.exec(select(User).order_by(User.id)))


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def update_user_admin(session: Session, user_id: int, data: UserUpdateAdmin) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise AppError("not_found", "User not found.", 404)
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def deactivate_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise AppError("not_found", "User not found.", 404)
    user.is_active = False
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
