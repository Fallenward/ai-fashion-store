import uuid
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai.provider import public_ai_config, save_ai_config
from app.ai.rag.ingest import ingest_product_catalog, ingest_store_documents, rebuild_vector_index
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.exceptions import AppError, NotFound
from app.core.text import slugify
from app.models import AgentAction, Category, ContactMessage, Conversation, KnowledgeDocument, Order, Product, Role, User
from app.services.catalog_admin import add_image, admin_product, archive_product, create_product, delete_image, update_product
from app.services.checkout_service import refund_order, update_order_status
from app.services.page_service import create_page, get_page, list_pages, page_admin_dict, publish_page, unpublish_page, update_page
from app.services.reporting import dashboard
from app.services.serializers import order_summary, public_user

router = APIRouter(prefix="/admin", tags=["admin"])


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    slug: str | None = None
    description: str | None = None
    image_url: str | None = None
    sort_order: int = 0


class VariantIn(BaseModel):
    sku: str = Field(min_length=2, max_length=64)
    size: str = Field(min_length=1, max_length=16)
    color: str = Field(min_length=1, max_length=40)
    color_hex: str = "#222222"
    price: Decimal | None = None
    quantity: int = Field(default=0, ge=0, le=100000)
    low_stock_threshold: int = Field(default=5, ge=0, le=1000)


class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str | None = None
    description: str = Field(min_length=2)
    brand: str = Field(min_length=1, max_length=80)
    category_id: uuid.UUID
    price: Decimal = Field(ge=0)
    compare_at_price: Decimal | None = None
    material: str | None = None
    care: str | None = None
    is_featured: bool = False
    is_new: bool = False
    is_bestseller: bool = False
    is_trending: bool = False
    is_active: bool = True
    variants: list[VariantIn] = Field(min_length=1)


class ProductPatch(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    brand: str | None = None
    category_id: uuid.UUID | None = None
    price: Decimal | None = None
    compare_at_price: Decimal | None = None
    material: str | None = None
    care: str | None = None
    is_featured: bool | None = None
    is_new: bool | None = None
    is_bestseller: bool | None = None
    is_trending: bool | None = None
    is_active: bool | None = None
    variants: list[VariantIn] | None = None


class StatusIn(BaseModel):
    status: str


class PageIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    slug: str | None = None
    summary: str | None = None
    definition: dict


class PagePatch(BaseModel):
    title: str | None = None
    slug: str | None = None
    summary: str | None = None
    definition: dict | None = None


class PublishIn(BaseModel):
    confirm: bool = False


class AIConfigIn(BaseModel):
    provider: str | None = None
    gemini_model: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    embedding_provider: str | None = None


@router.get("/stats")
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return dashboard(db)


@router.get("/categories")
def admin_categories(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()
    return [{"id": str(row.id), "name": row.name, "slug": row.slug, "description": row.description, "image_url": row.image_url, "sort_order": row.sort_order} for row in rows]


@router.post("/categories", status_code=201)
def post_category(payload: CategoryIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    slug = slugify(payload.slug or payload.name)
    if not slug:
        raise AppError("Enter a valid category address.")
    if db.scalar(select(Category.id).where(Category.slug == slug)):
        raise AppError("That category already exists.", 409)
    row = Category(name=payload.name.strip(), slug=slug, description=payload.description, image_url=payload.image_url, sort_order=payload.sort_order)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "name": row.name, "slug": row.slug}


@router.patch("/categories/{category_id}")
def patch_category(category_id: uuid.UUID, payload: CategoryIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(Category, category_id)
    if row is None:
        raise NotFound("Category not found.")
    row.name = payload.name.strip()
    row.description = payload.description
    row.image_url = payload.image_url
    row.sort_order = payload.sort_order
    if payload.slug:
        row.slug = slugify(payload.slug)
    db.commit()
    return {"id": str(row.id), "slug": row.slug, "name": row.name}


@router.get("/products")
def admin_products(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(Product).options(selectinload(Product.category)).order_by(Product.created_at.desc())).all()
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "slug": row.slug,
            "brand": row.brand,
            "price": f"{row.price:.2f}",
            "is_active": row.is_active,
            "category": row.category.name,
        }
        for row in rows
    ]


@router.post("/products", status_code=201)
def post_product(payload: ProductIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return create_product(db, payload.model_dump())


@router.get("/products/{product_id}")
def get_admin_product(product_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return admin_product(db, product_id)


@router.patch("/products/{product_id}")
def patch_product(product_id: uuid.UUID, payload: ProductPatch, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return update_product(db, product_id, payload.model_dump(exclude_unset=True))


@router.delete("/products/{product_id}")
def delete_product(product_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    archive_product(db, product_id)
    return {"ok": True}


@router.post("/products/{product_id}/images")
async def upload_image(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    allowed = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    if file.content_type not in allowed:
        raise AppError("Upload a JPEG, PNG, or WebP image.")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(f"Images must be under {settings.max_upload_mb} MB.")
    try:
        Image.open(BytesIO(content)).verify()
    except Exception as exc:
        raise AppError("That file is not a valid image.") from exc
    folder = Path(settings.upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{allowed[file.content_type]}"
    (folder / filename).write_bytes(content)
    return add_image(db, product_id, f"/uploads/{filename}", file.filename or "Product image")


@router.delete("/images/{image_id}")
def remove_image(image_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    delete_image(db, image_id)
    return {"ok": True}


@router.get("/orders")
def admin_orders(status: str | None = None, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(Order).options(selectinload(Order.items), selectinload(Order.payment)).order_by(Order.created_at.desc())
    if status:
        stmt = stmt.where(Order.status == status)
    return {"items": [order_summary(order) for order in db.scalars(stmt).all()]}


@router.get("/orders/{order_id}")
def admin_order(order_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from app.services.checkout_service import get_order

    return order_summary(get_order(db, admin, order_id))


@router.patch("/orders/{order_id}")
def patch_order(order_id: uuid.UUID, payload: StatusIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return update_order_status(db, order_id, payload.status)


@router.post("/orders/{order_id}/refund")
def refund(order_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return refund_order(db, order_id)


@router.get("/customers")
def customers(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).options(selectinload(User.role)).join(Role).where(Role.name == "customer").order_by(User.created_at.desc())).all()
    return [
        {"id": str(row.id), "email": row.email, "full_name": row.full_name, "is_active": row.is_active, "created_at": row.created_at.isoformat()}
        for row in rows
    ]


@router.get("/customers/{user_id}")
def customer_detail(user_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.scalar(select(User).options(selectinload(User.role), selectinload(User.profile), selectinload(User.style_profile), selectinload(User.addresses)).where(User.id == user_id))
    if user is None:
        raise NotFound("Customer not found.")
    orders = db.scalars(select(Order).options(selectinload(Order.items), selectinload(Order.payment)).where(Order.user_id == user.id).order_by(Order.created_at.desc())).all()
    style = user.style_profile
    return {
        "user": public_user(user),
        "addresses": [
            {"id": str(address.id), "label": address.label, "city": address.city, "region": address.region, "line1": address.line1, "is_default": address.is_default}
            for address in user.addresses
        ],
        "style": None
        if style is None
        else {
            "opted_out": style.opted_out,
            "preferred_sizes": style.preferred_sizes,
            "favorite_colors": style.favorite_colors,
            "favorite_categories": style.favorite_categories,
            "preferred_brands": style.preferred_brands,
            "notes": style.notes,
        },
        "orders": [order_summary(order) for order in orders],
    }


@router.get("/messages")
def messages(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(100)).all()
    return [
        {"id": str(row.id), "name": row.name, "email": row.email, "subject": row.subject, "message": row.message, "created_at": row.created_at.isoformat()}
        for row in rows
    ]


@router.get("/pages")
def admin_pages(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [
        {
            "id": str(page.id),
            "title": page.title,
            "slug": page.slug,
            "status": page.status,
            "summary": page.summary,
            "has_unpublished_changes": page.draft_definition != page.published_definition,
        }
        for page in list_pages(db)
    ]


@router.post("/pages", status_code=201)
def post_page(payload: PageIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = create_page(db, admin, payload.title, payload.definition, payload.slug, payload.summary)
    return page_admin_dict(db, get_page(db, page.id))


@router.get("/pages/{page_id}")
def get_admin_page(page_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return page_admin_dict(db, get_page(db, page_id))


@router.patch("/pages/{page_id}")
def patch_page(page_id: uuid.UUID, payload: PagePatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = update_page(db, admin, page_id, payload.model_dump(exclude_unset=True))
    return page_admin_dict(db, get_page(db, page.id))


@router.post("/pages/{page_id}/publish")
def publish(page_id: uuid.UUID, payload: PublishIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = publish_page(db, admin, page_id, payload.confirm)
    return page_admin_dict(db, get_page(db, page.id))


@router.post("/pages/{page_id}/unpublish")
def unpublish(page_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = unpublish_page(db, admin, page_id)
    return page_admin_dict(db, get_page(db, page.id))


@router.get("/ai/settings")
def get_ai(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return public_ai_config(db)


@router.put("/ai/settings")
def put_ai(payload: AIConfigIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return save_ai_config(db, payload.model_dump(exclude_unset=True))


@router.post("/ai/ingest/products")
def ingest_products(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ingest_product_catalog(db)


@router.post("/ai/ingest/documents")
def ingest_documents(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ingest_store_documents(db)


@router.post("/ai/reindex")
def reindex(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return rebuild_vector_index(db)


@router.get("/ai/knowledge")
def knowledge(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    documents = db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.source_type, KnowledgeDocument.title)).all()
    return [
        {
            "id": str(row.id),
            "title": row.title,
            "source_type": row.source_type,
            "source_id": row.source_id,
            "is_active": row.is_active,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in documents
    ]


@router.get("/ai/conversations")
def ai_conversations(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(Conversation).order_by(Conversation.updated_at.desc()).limit(100)).all()
    return [
        {"id": str(row.id), "title": row.title, "user_id": str(row.user_id) if row.user_id else None, "role_context": row.role_context, "updated_at": row.updated_at.isoformat()}
        for row in rows
    ]


@router.get("/ai/conversations/{conversation_id}")
def ai_conversation(conversation_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from app.ai.agent import get_my_messages

    return get_my_messages(db, admin, None, conversation_id)


@router.get("/ai/actions")
def actions(status: str | None = None, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(AgentAction).order_by(AgentAction.created_at.desc()).limit(200)
    if status:
        stmt = stmt.where(AgentAction.status == status)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": str(row.id),
            "tool_name": row.tool_name,
            "status": row.status,
            "error": row.error,
            "arguments": row.arguments,
            "result_summary": row.result_summary,
            "user_id": str(row.user_id) if row.user_id else None,
            "conversation_id": str(row.conversation_id) if row.conversation_id else None,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
