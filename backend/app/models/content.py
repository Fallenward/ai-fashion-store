import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Page(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pages"

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    draft_definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published_definition: Mapped[dict | None] = mapped_column(JSONB)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    versions: Mapped[list["PageVersion"]] = relationship(
        back_populates="page", cascade="all, delete-orphan", order_by="PageVersion.version_number"
    )


class PageVersion(Base, UUIDMixin):
    __tablename__ = "page_versions"

    page_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    note: Mapped[str | None] = mapped_column(String(200))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    page: Mapped[Page] = relationship(back_populates="versions")


class NewsletterSubscription(Base, UUIDMixin):
    __tablename__ = "newsletter_subscriptions"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ContactMessage(Base, UUIDMixin):
    __tablename__ = "contact_messages"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AppSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
