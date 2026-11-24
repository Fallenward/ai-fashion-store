from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.email import EmailAddress
from app.core.deps import get_current_user
from app.core.rate_limit import auth_limiter
from app.models import User
from app.services.auth_service import forgot_password, login_user, logout_user, refresh_session, register_user, reset_password
from app.services.serializers import public_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailAddress
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    guest_token: str | None = None


class LoginIn(BaseModel):
    email: EmailAddress
    password: str
    guest_token: str | None = None


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str | None = None


class ForgotIn(BaseModel):
    email: EmailAddress


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=72)


@router.post("/register", status_code=201)
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    auth_limiter.check(request)
    return register_user(db, payload.email, payload.password, payload.full_name, payload.guest_token)


@router.post("/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    auth_limiter.check(request)
    return login_user(db, payload.email, payload.password, payload.guest_token)


@router.post("/refresh")
def refresh(payload: RefreshIn, request: Request, db: Session = Depends(get_db)):
    auth_limiter.check(request)
    return refresh_session(db, payload.refresh_token)


@router.post("/logout")
def logout(payload: LogoutIn, db: Session = Depends(get_db)):
    logout_user(db, payload.refresh_token)
    return {"ok": True}


@router.post("/forgot-password")
def forgot(payload: ForgotIn, request: Request, db: Session = Depends(get_db)):
    auth_limiter.check(request)
    return forgot_password(db, payload.email)


@router.post("/reset-password")
def reset(payload: ResetIn, request: Request, db: Session = Depends(get_db)):
    auth_limiter.check(request)
    reset_password(db, payload.token, payload.password)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return public_user(user)
