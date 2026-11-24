import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Category(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(400))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "products"

    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    material: Mapped[str | None] = mapped_column(String(180))
    care: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_bestseller: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_trending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    popularity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    category: Mapped[Category] = relationship(back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order"
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductImage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "product_images"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(400), nullable=False)
    alt: Mapped[str] = mapped_column(String(180), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    product: Mapped[Product] = relationship(back_populates="images")


class ProductVariant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("sku", name="uq_variant_sku"),)

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    size: Mapped[str] = mapped_column(String(16), nullable=False)
    color: Mapped[str] = mapped_column(String(40), nullable=False)
    color_hex: Mapped[str] = mapped_column(String(7), nullable=False, default="#111111")
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    product: Mapped[Product] = relationship(back_populates="variants")
    inventory: Mapped["Inventory | None"] = relationship(
        back_populates="variant", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def unit_price(self) -> Decimal:
        return self.price if self.price is not None else self.product.price


class Inventory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "inventory"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), unique=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    variant: Mapped[ProductVariant] = relationship(back_populates="inventory")
