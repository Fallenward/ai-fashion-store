import re
import uuid
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models import Category, Product

_HTML = re.compile(r"[<>]")


def plain(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if _HTML.search(value):
        raise ValueError("HTML is not allowed in page content.")
    if "javascript:" in value.lower():
        raise ValueError("That link is not allowed.")
    if len(value) > limit:
        raise ValueError("Text is too long.")
    return value


def safe_href(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    value = value.strip()
    if value.startswith("/") and not value.startswith("//") and "\\" not in value and "<" not in value:
        return value[:180]
    raise ValueError("Links must be relative paths starting with /.")


def safe_image(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    value = value.strip()
    if value.startswith("/static/") or value.startswith("/uploads/"):
        return value[:400]
    if value.startswith("https://") and "<" not in value:
        return value[:400]
    raise ValueError("Use a site image path or an https URL.")


class Block(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HeroBlock(Block):
    type: Literal["hero"]
    eyebrow: str | None = None
    title: str
    subtitle: str | None = None
    image_url: str | None = None
    cta_label: str | None = None
    cta_href: str | None = None

    @field_validator("title")
    @classmethod
    def title_ok(cls, value: str) -> str:
        return plain(value, 160)

    @field_validator("subtitle")
    @classmethod
    def subtitle_ok(cls, value: str | None) -> str | None:
        return plain(value, 400) if value else None

    @field_validator("eyebrow")
    @classmethod
    def eyebrow_ok(cls, value: str | None) -> str | None:
        return plain(value, 80) if value else None

    @field_validator("cta_label")
    @classmethod
    def cta_ok(cls, value: str | None) -> str | None:
        return plain(value, 40) if value else None

    @field_validator("cta_href")
    @classmethod
    def href_ok(cls, value: str | None) -> str | None:
        return safe_href(value)

    @field_validator("image_url")
    @classmethod
    def image_ok(cls, value: str | None) -> str | None:
        return safe_image(value)


class TextBlock(Block):
    type: Literal["text"]
    heading: str | None = None
    body: str

    @field_validator("heading")
    @classmethod
    def heading_ok(cls, value: str | None) -> str | None:
        return plain(value, 160) if value else None

    @field_validator("body")
    @classmethod
    def body_ok(cls, value: str) -> str:
        if _HTML.search(value):
            raise ValueError("HTML is not allowed in page content.")
        value = value.strip()
        if len(value) > 4000:
            raise ValueError("Text is too long.")
        return value


class ImageBlock(Block):
    type: Literal["image"]
    image_url: str
    alt: str
    caption: str | None = None

    @field_validator("image_url")
    @classmethod
    def image_ok(cls, value: str) -> str:
        checked = safe_image(value)
        if not checked:
            raise ValueError("An image is required.")
        return checked

    @field_validator("alt")
    @classmethod
    def alt_ok(cls, value: str) -> str:
        return plain(value, 180)

    @field_validator("caption")
    @classmethod
    def caption_ok(cls, value: str | None) -> str | None:
        return plain(value, 240) if value else None


class ProductGridBlock(Block):
    type: Literal["product_grid"]
    title: str
    product_ids: list[uuid.UUID] = Field(min_length=1, max_length=12)

    @field_validator("title")
    @classmethod
    def title_ok(cls, value: str) -> str:
        return plain(value, 160)


class FeaturedCollectionBlock(Block):
    type: Literal["featured_collection"]
    title: str
    category_slug: str
    limit: int = Field(default=4, ge=1, le=12)

    @field_validator("title")
    @classmethod
    def title_ok(cls, value: str) -> str:
        return plain(value, 160)

    @field_validator("category_slug")
    @classmethod
    def slug_ok(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9-]{1,80}", value):
            raise ValueError("Unknown collection.")
        return value


class PromoBannerBlock(Block):
    type: Literal["promo_banner"]
    title: str
    subtitle: str | None = None
    cta_label: str | None = None
    cta_href: str | None = None
    tone: Literal["dark", "light"] = "dark"

    @field_validator("title")
    @classmethod
    def title_ok(cls, value: str) -> str:
        return plain(value, 160)

    @field_validator("subtitle")
    @classmethod
    def subtitle_ok(cls, value: str | None) -> str | None:
        return plain(value, 300) if value else None

    @field_validator("cta_label")
    @classmethod
    def cta_ok(cls, value: str | None) -> str | None:
        return plain(value, 40) if value else None

    @field_validator("cta_href")
    @classmethod
    def href_ok(cls, value: str | None) -> str | None:
        return safe_href(value)


class Quote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quote: str
    author: str
    detail: str | None = None

    @field_validator("quote")
    @classmethod
    def quote_ok(cls, value: str) -> str:
        return plain(value, 400)

    @field_validator("author")
    @classmethod
    def author_ok(cls, value: str) -> str:
        return plain(value, 80)

    @field_validator("detail")
    @classmethod
    def detail_ok(cls, value: str | None) -> str | None:
        return plain(value, 80) if value else None


class TestimonialsBlock(Block):
    type: Literal["testimonials"]
    title: str
    quotes: list[Quote] = Field(min_length=1, max_length=6)

    @field_validator("title")
    @classmethod
    def title_ok(cls, value: str) -> str:
        return plain(value, 160)


class FaqItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    answer: str

    @field_validator("question")
    @classmethod
    def question_ok(cls, value: str) -> str:
        return plain(value, 180)

    @field_validator("answer")
    @classmethod
    def answer_ok(cls, value: str) -> str:
        if _HTML.search(value):
            raise ValueError("HTML is not allowed in page content.")
        value = value.strip()
        if len(value) > 1200:
            raise ValueError("Text is too long.")
        return value


class FaqBlock(Block):
    type: Literal["faq"]
    title: str
    items: list[FaqItem] = Field(min_length=1, max_length=12)

    @field_validator("title")
    @classmethod
    def title_ok(cls, value: str) -> str:
        return plain(value, 160)


class NewsletterBlock(Block):
    type: Literal["newsletter"]
    title: str
    subtitle: str | None = None

    @field_validator("title")
    @classmethod
    def title_ok(cls, value: str) -> str:
        return plain(value, 160)

    @field_validator("subtitle")
    @classmethod
    def subtitle_ok(cls, value: str | None) -> str | None:
        return plain(value, 300) if value else None


BlockUnion = Annotated[
    Union[
        HeroBlock,
        TextBlock,
        ImageBlock,
        ProductGridBlock,
        FeaturedCollectionBlock,
        PromoBannerBlock,
        TestimonialsBlock,
        FaqBlock,
        NewsletterBlock,
    ],
    Field(discriminator="type"),
]


class PageDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    blocks: list[BlockUnion] = Field(min_length=1, max_length=30)


def validate_definition(db: Session, raw: dict) -> dict:
    try:
        definition = PageDefinition.model_validate(raw)
    except Exception as exc:
        raise AppError(f"Page definition is not valid: {exc}") from exc
    data = definition.model_dump(mode="json")
    for block in data["blocks"]:
        if block["type"] == "product_grid":
            ids = [uuid.UUID(value) for value in block["product_ids"]]
            found = set(db.scalars(select(Product.id).where(Product.id.in_(ids), Product.is_active.is_(True))).all())
            missing = [str(value) for value in ids if value not in found]
            if missing:
                raise AppError("Some products in the page do not exist or are inactive.")
        if block["type"] == "featured_collection":
            category = db.scalar(select(Category).where(Category.slug == block["category_slug"]))
            if category is None:
                raise AppError(f"Unknown collection '{block['category_slug']}'.")
    return data
