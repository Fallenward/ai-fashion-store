from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import AppError, Unauthorized
from app.core.security import create_access_token, hash_password, hash_token, new_secret, verify_password
from app.models import CustomerProfile, CustomerStyleProfile, PasswordResetToken, RefreshToken, Role, User
from app.services.cart_service import merge_guest_cart
from app.services.serializers import public_user


def _role(db: Session, name: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name)
        db.add(role)
        db.flush()
    return role


def register_user(db: Session, email: str, password: str, full_name: str, guest_token: str | None = None) -> dict:
    email = email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise AppError("An account with that email already exists.", 409)
    if len(password) < 8 or len(password) > 72:
        raise AppError("Use a password between 8 and 72 characters.")
    if len(full_name.strip()) < 2:
        raise AppError("Enter your name.")
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role=_role(db, "customer"),
    )
    db.add(user)
    db.flush()
    db.add(CustomerProfile(user_id=user.id))
    db.add(CustomerStyleProfile(user_id=user.id))
    db.commit()
    user = _load(db, user.id)
    merge_guest_cart(db, user, guest_token)
    return _tokens(db, user)


def login_user(db: Session, email: str, password: str, guest_token: str | None = None) -> dict:
    user = db.scalar(
        select(User).options(selectinload(User.role), selectinload(User.profile)).where(User.email == email.strip().lower())
    )
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise Unauthorized("Invalid email or password.")
    merge_guest_cart(db, user, guest_token)
    return _tokens(db, user)


def refresh_session(db: Session, raw_token: str) -> dict:
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
    now = datetime.now(timezone.utc)
    if row is None or row.revoked_at is not None or row.expires_at < now:
        raise Unauthorized("Refresh token is invalid.")
    user = _load(db, row.user_id)
    if not user.is_active:
        raise Unauthorized("This account is disabled.")
    row.revoked_at = now
    db.commit()
    return _tokens(db, user)


def logout_user(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()


def forgot_password(db: Session, email: str) -> dict:
    user = db.scalar(select(User).where(User.email == email.strip().lower(), User.is_active.is_(True)))
    response = {"message": "If an account exists for that email, a reset token has been created."}
    if user is None:
        return response
    raw = new_secret()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    db.commit()
    if get_settings().dev_reset_tokens:
        response["reset_token"] = raw
        response["dev_note"] = "Email delivery is not configured. This development token is shown so you can finish the reset."
    return response


def reset_password(db: Session, raw_token: str, password: str) -> None:
    if len(password) < 8 or len(password) > 72:
        raise AppError("Use a password between 8 and 72 characters.")
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(raw_token)))
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or row.expires_at < now:
        raise AppError("That reset link is invalid or expired.")
    user = db.get(User, row.user_id)
    if user is None:
        raise AppError("That reset link is invalid or expired.")
    user.password_hash = hash_password(password)
    row.used_at = now
    for token in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))):
        token.revoked_at = now
    db.commit()


def _load(db: Session, user_id) -> User:
    user = db.scalar(select(User).options(selectinload(User.role), selectinload(User.profile)).where(User.id == user_id))
    if user is None:
        raise Unauthorized("Invalid or expired token.")
    return user


def _tokens(db: Session, user: User) -> dict:
    settings = get_settings()
    raw = new_secret()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    return {
        "access_token": create_access_token(user.id, user.role_name),
        "refresh_token": raw,
        "token_type": "bearer",
        "user": public_user(user),
    }
