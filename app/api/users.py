from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlmodel import Session

from app.auth import create_access_token, get_current_user
from app.rate_limit import limiter
from app.database import get_session
from app.middleware.auth_middleware import RequirePermission
from app.models import User
from app.schemas import TokenResponse, UserLogin, UserOut, UserSignup, UserUpdateAdmin
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def signup(request: Request, body: UserSignup, session: Annotated[Session, Depends(get_session)]):
    user = user_service.create_user(session, body)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("30/minute")
def login(request: Request, body: UserLogin, session: Annotated[Session, Depends(get_session)]):
    user = user_service.authenticate(session, body.email, body.password)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user


@router.get("", response_model=list[UserOut])
def list_users(
    _: Annotated[User, Depends(RequirePermission("manage_users"))],
    session: Annotated[Session, Depends(get_session)],
):
    return user_service.list_users(session)


@router.patch("/{user_id}", response_model=UserOut)
def patch_user(
    user_id: int,
    body: UserUpdateAdmin,
    _: Annotated[User, Depends(RequirePermission("manage_users"))],
    session: Annotated[Session, Depends(get_session)],
):
    return user_service.update_user_admin(session, user_id, body)


@router.patch("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: int,
    _: Annotated[User, Depends(RequirePermission("manage_users"))],
    session: Annotated[Session, Depends(get_session)],
):
    return user_service.deactivate_user(session, user_id)
