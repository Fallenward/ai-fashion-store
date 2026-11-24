import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppError, NotFound, Unauthorized
from app.core.money import money, q
from app.core.security import hash_password, verify_password
from app.models import Address, CustomerStyleProfile, User
from app.services.serializers import address_dict


def update_profile(db: Session, user: User, full_name: str | None, phone: str | None) -> User:
    if full_name is not None:
        cleaned = full_name.strip()
        if len(cleaned) < 2:
            raise AppError("Enter your name.")
        user.full_name = cleaned
    if phone is not None and user.profile is not None:
        user.profile.phone = phone.strip() or None
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise Unauthorized("Current password is incorrect.")
    if len(new_password) < 8:
        raise AppError("Use at least 8 characters.")
    user.password_hash = hash_password(new_password)
    from app.models import RefreshToken

    for token in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))):
        from datetime import datetime, timezone

        token.revoked_at = datetime.now(timezone.utc)
    db.commit()


def list_addresses(db: Session, user: User) -> list[dict]:
    rows = db.scalars(select(Address).where(Address.user_id == user.id).order_by(Address.is_default.desc(), Address.created_at)).all()
    return [address_dict(row) for row in rows]


def create_address(db: Session, user: User, payload: dict) -> dict:
    if payload.get("is_default"):
        for row in db.scalars(select(Address).where(Address.user_id == user.id)):
            row.is_default = False
    address = Address(user_id=user.id, **_address_fields(payload))
    db.add(address)
    db.commit()
    db.refresh(address)
    return address_dict(address)


def update_address(db: Session, user: User, address_id: uuid.UUID, payload: dict) -> dict:
    address = db.get(Address, address_id)
    if address is None or address.user_id != user.id:
        raise NotFound("Address not found.")
    if payload.get("is_default"):
        for row in db.scalars(select(Address).where(Address.user_id == user.id)):
            row.is_default = False
    for key, value in _address_fields(payload).items():
        setattr(address, key, value)
    db.commit()
    db.refresh(address)
    return address_dict(address)


def delete_address(db: Session, user: User, address_id: uuid.UUID) -> None:
    address = db.get(Address, address_id)
    if address is None or address.user_id != user.id:
        raise NotFound("Address not found.")
    db.delete(address)
    db.commit()


def _address_fields(payload: dict) -> dict:
    required = ["full_name", "line1", "city", "region", "postal_code", "country"]
    if any(not str(payload.get(field, "")).strip() for field in required):
        raise AppError("A complete address is required.")
    return {
        "label": (payload.get("label") or "Home").strip()[:40],
        "full_name": payload["full_name"].strip(),
        "line1": payload["line1"].strip(),
        "line2": (payload.get("line2") or "").strip() or None,
        "city": payload["city"].strip(),
        "region": payload["region"].strip(),
        "postal_code": payload["postal_code"].strip(),
        "country": payload["country"].strip(),
        "phone": (payload.get("phone") or "").strip() or None,
        "is_default": bool(payload.get("is_default")),
    }


def _style(db: Session, user: User) -> CustomerStyleProfile:
    profile = db.scalar(select(CustomerStyleProfile).where(CustomerStyleProfile.user_id == user.id))
    if profile is None:
        profile = CustomerStyleProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def style_payload(profile: CustomerStyleProfile) -> dict:
    return {
        "preferred_sizes": profile.preferred_sizes or [],
        "favorite_colors": profile.favorite_colors or [],
        "favorite_categories": profile.favorite_categories or [],
        "preferred_brands": profile.preferred_brands or [],
        "style_keywords": profile.style_keywords or [],
        "budget_min": money(profile.budget_min) if profile.budget_min is not None else None,
        "budget_max": money(profile.budget_max) if profile.budget_max is not None else None,
        "notes": profile.notes,
        "opted_out": profile.opted_out,
    }


def get_style(db: Session, user: User) -> dict:
    return style_payload(_style(db, user))


def _clean_list(values: list[str] | None, limit: int = 12) -> list[str]:
    if not values:
        return []
    cleaned = []
    for value in values:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text[:40])
    return cleaned[:limit]


def save_style(db: Session, user: User, payload: dict) -> dict:
    profile = _style(db, user)
    if payload.get("opt_out") is True:
        return opt_out_style(db, user)
    profile.opted_out = False
    for field in ("preferred_sizes", "favorite_colors", "favorite_categories", "preferred_brands", "style_keywords"):
        if field in payload and payload[field] is not None:
            setattr(profile, field, _clean_list(payload[field]))
    if "budget_min" in payload:
        profile.budget_min = q(payload["budget_min"]) if payload["budget_min"] not in (None, "") else None
    if "budget_max" in payload:
        profile.budget_max = q(payload["budget_max"]) if payload["budget_max"] not in (None, "") else None
    if profile.budget_min is not None and profile.budget_max is not None and profile.budget_max < profile.budget_min:
        raise AppError("Maximum budget must be greater than the minimum.")
    if "notes" in payload:
        notes = (payload.get("notes") or "").strip()
        profile.notes = notes[:1000] or None
    db.commit()
    db.refresh(profile)
    return style_payload(profile)


def clear_style(db: Session, user: User) -> dict:
    profile = _style(db, user)
    profile.preferred_sizes = []
    profile.favorite_colors = []
    profile.favorite_categories = []
    profile.preferred_brands = []
    profile.style_keywords = []
    profile.budget_min = None
    profile.budget_max = None
    profile.notes = None
    profile.opted_out = False
    db.commit()
    db.refresh(profile)
    return style_payload(profile)


def opt_out_style(db: Session, user: User) -> dict:
    profile = _style(db, user)
    profile.preferred_sizes = []
    profile.favorite_colors = []
    profile.favorite_categories = []
    profile.preferred_brands = []
    profile.style_keywords = []
    profile.budget_min = None
    profile.budget_max = None
    profile.notes = None
    profile.opted_out = True
    db.commit()
    db.refresh(profile)
    return style_payload(profile)


def opt_in_style(db: Session, user: User) -> dict:
    profile = _style(db, user)
    profile.opted_out = False
    db.commit()
    db.refresh(profile)
    return style_payload(profile)


def style_for_agent(db: Session, user: User | None) -> dict | None:
    if user is None:
        return None
    profile = db.scalar(select(CustomerStyleProfile).where(CustomerStyleProfile.user_id == user.id))
    if profile is None or profile.opted_out:
        return {"opted_out": True}
    return style_payload(profile)
