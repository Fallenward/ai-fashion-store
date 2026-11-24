import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppError, NotFound, PermissionDenied
from app.core.text import slugify
from app.models import Page, PageVersion, User
from app.repositories.product_repository import ProductSearch, search_products
from app.services.page_schema import validate_definition
from app.services.serializers import product_card


def _unique_slug(db: Session, title: str, requested: str | None = None) -> str:
    base = slugify(requested or title) or "page"
    slug = base
    index = 2
    while db.scalar(select(Page.id).where(Page.slug == slug)) is not None:
        slug = f"{base}-{index}"
        index += 1
    return slug


def _snapshot(db: Session, page: Page, user: User | None, note: str) -> None:
    current = db.scalar(select(func.max(PageVersion.version_number)).where(PageVersion.page_id == page.id)) or 0
    db.add(
        PageVersion(
            page_id=page.id,
            version_number=int(current) + 1,
            definition=page.draft_definition,
            note=note,
            created_by_id=user.id if user else None,
        )
    )


def create_page(db: Session, user: User, title: str, definition: dict, slug: str | None = None, summary: str | None = None) -> Page:
    if not user.is_admin:
        raise PermissionDenied("Only an administrator can create pages.")
    page = Page(
        title=title.strip()[:180],
        slug=_unique_slug(db, title, slug),
        summary=(summary or "").strip()[:500] or None,
        status="draft",
        draft_definition=validate_definition(db, definition),
        created_by_id=user.id,
    )
    db.add(page)
    db.flush()
    _snapshot(db, page, user, "Created draft")
    db.commit()
    db.refresh(page)
    return page


def update_page(db: Session, user: User, page_id: uuid.UUID, payload: dict) -> Page:
    if not user.is_admin:
        raise PermissionDenied("Only an administrator can edit pages.")
    page = _page(db, page_id)
    if "title" in payload and payload["title"]:
        page.title = str(payload["title"]).strip()[:180]
    if "summary" in payload:
        page.summary = (payload.get("summary") or "").strip()[:500] or None
    if "slug" in payload and payload["slug"]:
        if page.status == "published":
            raise AppError("Unpublish the page before changing its address.")
        new_slug = slugify(payload["slug"])
        if not new_slug:
            raise AppError("Enter a valid page address.")
        existing = db.scalar(select(Page.id).where(Page.slug == new_slug, Page.id != page.id))
        if existing:
            raise AppError("That address is already used.")
        page.slug = new_slug
    if "definition" in payload and payload["definition"] is not None:
        page.draft_definition = validate_definition(db, payload["definition"])
        _snapshot(db, page, user, "Edited draft")
    db.commit()
    db.refresh(page)
    return page


def publish_page(db: Session, user: User, page_id: uuid.UUID, confirm: bool) -> Page:
    if not user.is_admin:
        raise PermissionDenied("Only an administrator can publish pages.")
    if not confirm:
        raise AppError("Publishing requires explicit confirmation.")
    page = _page(db, page_id)
    from datetime import datetime, timezone

    page.published_definition = page.draft_definition
    page.status = "published"
    page.published_at = datetime.now(timezone.utc)
    _snapshot(db, page, user, "Published")
    db.commit()
    db.refresh(page)
    return page


def unpublish_page(db: Session, user: User, page_id: uuid.UUID) -> Page:
    if not user.is_admin:
        raise PermissionDenied("Only an administrator can unpublish pages.")
    page = _page(db, page_id)
    page.status = "draft"
    db.commit()
    db.refresh(page)
    return page


def _page(db: Session, page_id: uuid.UUID) -> Page:
    page = db.scalar(select(Page).options(selectinload(Page.versions)).where(Page.id == page_id))
    if page is None:
        raise NotFound("Page not found.")
    return page


def get_page(db: Session, page_id: uuid.UUID) -> Page:
    return _page(db, page_id)


def list_pages(db: Session, published_only: bool = False) -> list[Page]:
    stmt = select(Page).order_by(Page.updated_at.desc())
    if published_only:
        stmt = stmt.where(Page.status == "published")
    return list(db.scalars(stmt).all())


def get_published_by_slug(db: Session, slug: str) -> Page:
    page = db.scalar(select(Page).where(Page.slug == slug, Page.status == "published"))
    if page is None or not page.published_definition:
        raise NotFound("Page not found.")
    return page


def resolve_definition(db: Session, definition: dict) -> dict:
    blocks = []
    for block in definition.get("blocks", []):
        resolved = dict(block)
        if block.get("type") == "product_grid":
            ids = []
            for raw in block.get("product_ids", []):
                try:
                    ids.append(uuid.UUID(str(raw)))
                except ValueError:
                    continue
            products, _ = search_products(db, ProductSearch(ids=ids, page_size=max(len(ids), 1)))
            order = {value: index for index, value in enumerate(ids)}
            products = sorted(products, key=lambda product: order.get(product.id, 999))
            resolved["products"] = [product_card(product) for product in products]
        if block.get("type") == "featured_collection":
            products, _ = search_products(
                db,
                ProductSearch(
                    category=block.get("category_slug"),
                    in_stock=True,
                    page_size=int(block.get("limit") or 4),
                    sort="popularity",
                ),
            )
            resolved["products"] = [product_card(product) for product in products]
        blocks.append(resolved)
    return {"blocks": blocks}


def page_admin_dict(db: Session, page: Page) -> dict:
    return {
        "id": str(page.id),
        "title": page.title,
        "slug": page.slug,
        "summary": page.summary,
        "status": page.status,
        "draft_definition": page.draft_definition,
        "published_definition": resolve_definition(db, page.published_definition) if page.published_definition else None,
        "resolved_draft": resolve_definition(db, page.draft_definition),
        "has_unpublished_changes": page.draft_definition != page.published_definition,
        "published_at": page.published_at.isoformat() if page.published_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
        "versions": [
            {"id": str(version.id), "version_number": version.version_number, "note": version.note, "created_at": version.created_at.isoformat()}
            for version in sorted(page.versions, key=lambda item: item.version_number, reverse=True)
        ],
    }


def page_public_dict(db: Session, page: Page) -> dict:
    return {
        "id": str(page.id),
        "title": page.title,
        "slug": page.slug,
        "summary": page.summary,
        "definition": resolve_definition(db, page.published_definition or {"blocks": []}),
    }
