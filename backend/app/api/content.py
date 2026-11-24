from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.email import EmailAddress
from app.core.exceptions import AppError
from app.models import ContactMessage, NewsletterSubscription
from app.services.page_service import get_published_by_slug, list_pages, page_public_dict

router = APIRouter(tags=["content"])


class NewsletterIn(BaseModel):
    email: EmailAddress


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailAddress
    subject: str = Field(min_length=2, max_length=180)
    message: str = Field(min_length=5, max_length=4000)


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    settings = get_settings()
    provider = settings.llm_provider
    configured = False
    if provider == "gemini":
        configured = bool(settings.gemini_api_key.strip())
    elif provider == "ollama":
        configured = bool(settings.ollama_model.strip())
    return {
        "status": "ok",
        "database": "ok",
        "ai_configured": configured,
        "payments": "stripe" if settings.stripe_enabled else "mock",
    }


@router.post("/newsletter")
def newsletter(payload: NewsletterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    existing = db.scalar(select(NewsletterSubscription).where(NewsletterSubscription.email == email))
    if existing is None:
        db.add(NewsletterSubscription(email=email, is_active=True))
    else:
        existing.is_active = True
    db.commit()
    return {"ok": True, "message": "You are on the list."}


@router.post("/contact", status_code=201)
def contact(payload: ContactIn, db: Session = Depends(get_db)):
    if "<" in payload.message or "<" in payload.subject:
        raise AppError("HTML is not allowed in messages.")
    db.add(ContactMessage(name=payload.name.strip(), email=payload.email.lower(), subject=payload.subject.strip(), message=payload.message.strip()))
    db.commit()
    return {"ok": True, "message": "Message received. The studio will read it in the admin inbox."}


@router.get("/pages")
def pages(db: Session = Depends(get_db)):
    return [
        {"id": str(page.id), "title": page.title, "slug": page.slug, "summary": page.summary}
        for page in list_pages(db, published_only=True)
    ]


@router.get("/pages/{slug}")
def page(slug: str, db: Session = Depends(get_db)):
    return page_public_dict(db, get_published_by_slug(db, slug))
