import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    role: Mapped[Role] = relationship(back_populates="users")
    profile: Mapped["CustomerProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    style_profile: Mapped["CustomerStyleProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    addresses: Mapped[list["Address"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else "customer"

    @property
    def is_admin(self) -> bool:
        return self.role_name == "admin"


class CustomerProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    user: Mapped[User] = relationship(back_populates="profile")


class CustomerStyleProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customer_style_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    preferred_sizes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    favorite_colors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    favorite_categories: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    preferred_brands: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    style_keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    opted_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    user: Mapped[User] = relationship(back_populates="style_profile")


class Address(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "addresses"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(40), nullable=False, default="Home")
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    line1: Mapped[str] = mapped_column(String(180), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(180))
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="United States")
    phone: Mapped[str | None] = mapped_column(String(30))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    user: Mapped[User] = relationship(back_populates="addresses")


class RefreshToken(Base, UUIDMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PasswordResetToken(Base, UUIDMixin):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
