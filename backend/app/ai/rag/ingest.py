import hashlib
import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.ai.embeddings import embed_texts
from app.ai.rag.documents import STORE_DOCUMENTS, product_text
from app.models import Category, KnowledgeChunk, KnowledgeDocument, Product

logger = logging.getLogger(__name__)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def chunk_text(text: str, size: int = 700, overlap: int = 80) -> list[str]:
    paragraphs: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= size:
            paragraphs.append(paragraph)
            continue
        start = 0
        while start < len(paragraph):
            paragraphs.append(paragraph[start : start + size])
            start += max(size - overlap, 1)
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 1 > size:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks or [text[:size]]


def upsert_document(db: Session, source_type: str, source_id: str, title: str, content: str) -> bool:
    content_hash = _hash(content)
    document = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.source_type == source_type,
            KnowledgeDocument.source_id == source_id,
        )
    )
    if document and document.content_hash == content_hash and document.is_active:
        return False
    if document is None:
        document = KnowledgeDocument(
            source_type=source_type,
            source_id=source_id,
            title=title,
            content=content,
            content_hash=content_hash,
        )
        db.add(document)
        db.flush()
    else:
        document.title = title
        document.content = content
        document.content_hash = content_hash
        document.is_active = True
        db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
    parts = chunk_text(content)
    vectors = embed_texts(parts)
    for index, (part, vector) in enumerate(zip(parts, vectors)):
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=index,
                content=part,
                content_hash=_hash(part),
                embedding=vector,
            )
        )
    return True


def ingest_product_catalog(db: Session) -> dict:
    products = db.scalars(
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.variants))
        .where(Product.is_active.is_(True))
    ).all()
    updated = 0
    for product in products:
        if upsert_document(db, "product", str(product.id), product.name, product_text(product)):
            updated += 1
    active_ids = {str(product.id) for product in products}
    stale = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source_type == "product")).all()
    removed = 0
    for document in stale:
        if document.source_id not in active_ids:
            document.is_active = False
            removed += 1
    db.commit()
    return {"updated": updated, "products": len(products), "deactivated": removed}


def ingest_store_documents(db: Session) -> dict:
    updated = 0
    for document in STORE_DOCUMENTS:
        if upsert_document(db, "policy", document["source_id"], document["title"], document["content"]):
            updated += 1
    db.commit()
    return {"updated": updated, "documents": len(STORE_DOCUMENTS)}


def rebuild_vector_index(db: Session) -> dict:
    chunks = db.scalars(
        select(KnowledgeChunk).join(KnowledgeDocument).where(KnowledgeDocument.is_active.is_(True))
    ).all()
    if not chunks:
        return {"rebuilt": 0}
    vectors = embed_texts([chunk.content for chunk in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk.embedding = vector
    db.commit()
    logger.info("Rebuilt %s knowledge embeddings", len(chunks))
    return {"rebuilt": len(chunks)}
