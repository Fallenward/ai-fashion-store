import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.services.account_service import (
    change_password,
    clear_style,
    create_address,
    delete_address,
    get_style,
    list_addresses,
    opt_in_style,
    opt_out_style,
    save_style,
    update_address,
    update_profile,
)
from app.services.serializers import public_user

router = APIRouter(prefix="/account", tags=["account"])


class ProfileIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class AddressIn(BaseModel):
    label: str | None = None
    full_name: str
    line1: str
    line2: str | None = None
    city: str
    region: str
    postal_code: str
    country: str = "United States"
    phone: str | None = None
    is_default: bool = False


class StyleIn(BaseModel):
    preferred_sizes: list[str] | None = None
    favorite_colors: list[str] | None = None
    favorite_categories: list[str] | None = None
    preferred_brands: list[str] | None = None
    style_keywords: list[str] | None = None
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    notes: str | None = None
    opt_out: bool | None = None


@router.patch("/profile")
def patch_profile(payload: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_profile(db, user, payload.full_name, payload.phone)
    return public_user(user)


@router.post("/password")
def password(payload: PasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    change_password(db, user, payload.current_password, payload.new_password)
    return {"ok": True}


@router.get("/addresses")
def addresses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": list_addresses(db, user)}


@router.post("/addresses", status_code=201)
def post_address(payload: AddressIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_address(db, user, payload.model_dump())


@router.patch("/addresses/{address_id}")
def patch_address(address_id: uuid.UUID, payload: AddressIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_address(db, user, address_id, payload.model_dump())


@router.delete("/addresses/{address_id}")
def remove_address(address_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_address(db, user, address_id)
    return {"ok": True}


@router.get("/style")
def style(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_style(db, user)


@router.put("/style")
def put_style(payload: StyleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return save_style(db, user, payload.model_dump(exclude_unset=True))


@router.delete("/style")
def delete_style(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return clear_style(db, user)


@router.post("/style/opt-out")
def style_out(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return opt_out_style(db, user)


@router.post("/style/opt-in")
def style_in(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return opt_in_style(db, user)
