import logging

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.embeddings import embed_texts
from app.models import KnowledgeChunk, KnowledgeDocument

logger = logging.getLogger(__name__)


def _row(chunk: KnowledgeChunk, document: KnowledgeDocument, score: float) -> dict:
    return {
        "chunk_id": str(chunk.id),
        "title": document.title,
        "content": chunk.content[:800],
        "source_type": document.source_type,
        "source_id": document.source_id,
        "product_id": document.source_id if document.source_type == "product" else None,
        "score": round(float(score), 4),
    }


def _keyword(db: Session, query: str, limit: int) -> list[dict]:
    cleaned = " ".join(query.split())
    if not cleaned:
        return []
    tsquery = func.plainto_tsquery("english", cleaned)
    tsvector = func.to_tsvector("english", KnowledgeChunk.content)
    try:
        rows = db.execute(
            select(KnowledgeChunk, KnowledgeDocument, func.ts_rank(tsvector, tsquery).label("rank"))
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.is_active.is_(True), tsvector.op("@@")(tsquery))
            .order_by(func.ts_rank(tsvector, tsquery).desc())
            .limit(limit)
        ).all()
    except Exception:
        db.rollback()
        rows = []
    if rows:
        return [_row(chunk, document, float(rank or 0)) for chunk, document, rank in rows]
    like = f"%{cleaned[:80]}%"
    fallback = db.execute(
        select(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(
            KnowledgeDocument.is_active.is_(True),
            or_(KnowledgeChunk.content.ilike(like), KnowledgeDocument.title.ilike(like)),
        )
        .limit(limit)
    ).all()
    return [_row(chunk, document, 0.2) for chunk, document in fallback]


def _vector(db: Session, query: str, limit: int) -> list[dict]:
    vector = embed_texts([query])[0]
    distance = KnowledgeChunk.embedding.cosine_distance(vector)
    rows = db.execute(
        select(KnowledgeChunk, KnowledgeDocument, distance.label("distance"))
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeDocument.is_active.is_(True), KnowledgeChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    ).all()
    results = []
    for chunk, document, dist in rows:
        score = 1 - float(dist or 1)
        if score > 0.05:
            results.append(_row(chunk, document, score))
    return results


def search_knowledge(db: Session, query: str, limit: int = 5) -> list[dict]:
    merged: dict[str, dict] = {}
    for item in _keyword(db, query, limit):
        merged[item["chunk_id"]] = item
    try:
        for item in _vector(db, query, limit):
            current = merged.get(item["chunk_id"])
            if current is None or item["score"] > current["score"]:
                merged[item["chunk_id"]] = item
    except Exception:
        logger.exception("Vector search failed; using keyword results only")
        db.rollback()
    ranked = sorted(merged.values(), key=lambda item: item["score"], reverse=True)
    return ranked[:limit]
