from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChatMessage, Conversation


def recent_messages(db: Session, conversation: Conversation, limit: int = 12) -> list[dict]:
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id, ChatMessage.role.in_(["user", "assistant"]))
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    ).all()
    ordered = list(reversed(rows))
    return [{"role": row.role, "content": row.content} for row in ordered]
