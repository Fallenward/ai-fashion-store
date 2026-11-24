import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Cart(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "carts"

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    guest_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id", name="uq_cart_variant"),
        CheckConstraint("quantity > 0", name="ck_cart_item_qty"),
    )

    cart_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    cart: Mapped[Cart] = relationship(back_populates="items")
    variant: Mapped["ProductVariant"] = relationship()


class Wishlist(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wishlists"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    items: Mapped[list["WishlistItem"]] = relationship(back_populates="wishlist", cascade="all, delete-orphan")


class WishlistItem(Base, UUIDMixin):
    __tablename__ = "wishlist_items"
    __table_args__ = (UniqueConstraint("wishlist_id", "product_id", name="uq_wishlist_product"),)

    wishlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wishlists.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    wishlist: Mapped[Wishlist] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class PromoCode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "promo_codes"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    percent_off: Mapped[int | None] = mapped_column(Integer)
    amount_off: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    min_subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_address: Mapped[dict] = mapped_column(JSONB, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    promo_code: Mapped[str | None] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payment: Mapped["Payment | None"] = relationship(back_populates="order", uselist=False, cascade="all, delete-orphan")
    user: Mapped["User"] = relationship()


class OrderItem(Base, UUIDMixin):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_item_qty"),)

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"))
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    size: Mapped[str] = mapped_column(String(16), nullable=False)
    color: Mapped[str] = mapped_column(String(40), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(400))
    order: Mapped[Order] = relationship(back_populates="items")


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    stripe_session_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    stripe_payment_intent: Mapped[str | None] = mapped_column(String(255))
    order: Mapped[Order] = relationship(back_populates="payment")
