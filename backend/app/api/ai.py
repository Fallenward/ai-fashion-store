import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.agent import get_my_messages, list_my_conversations, run_agent
from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user, guest_token
from app.core.rate_limit import ai_limiter
from app.models import User

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None


@router.post("/chat")
def chat(
    payload: ChatIn,
    request: Request,
    user: User | None = Depends(get_optional_user),
    token: str | None = Depends(guest_token),
    db: Session = Depends(get_db),
):
    ai_limiter.check(request)
    return run_agent(db, message=payload.message, user=user, conversation_id=payload.conversation_id, guest_token=token)


@router.get("/conversations")
def conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": list_my_conversations(db, user)}


@router.get("/conversations/{conversation_id}")
def conversation(
    conversation_id: uuid.UUID,
    user: User | None = Depends(get_optional_user),
    token: str | None = Depends(guest_token),
    db: Session = Depends(get_db),
):
    return get_my_messages(db, user, token, conversation_id)
