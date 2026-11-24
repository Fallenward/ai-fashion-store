import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.exceptions import PermissionDenied, Unauthorized
from app.core.security import decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_by_token(db: Session, token: str) -> User:
    payload = decode_access_token(token)
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError as exc:
        raise Unauthorized("Invalid or expired token.") from exc
    user = db.scalar(select(User).options(selectinload(User.role), selectinload(User.profile)).where(User.id == user_id))
    if user is None or not user.is_active:
        raise Unauthorized("Invalid or expired token.")
    return user


def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    return get_user_by_token(db, credentials.credentials)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise Unauthorized()
    return get_user_by_token(db, credentials.credentials)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise PermissionDenied("Admin access is required.")
    return user


def cart_token(x_cart_token: Annotated[str | None, Header()] = None) -> str | None:
    if x_cart_token:
        return x_cart_token.strip()[:64] or None
    return None


def guest_token(x_guest_token: Annotated[str | None, Header()] = None) -> str | None:
    if x_guest_token:
        return x_guest_token.strip()[:64] or None
    return None
