import re
import uuid

from app.core.exceptions import PermissionDenied
from app.services.page_service import create_page, get_page, page_admin_dict, publish_page, unpublish_page, update_page

_PUBLISH = re.compile(r"\b(publish|go live|make it live|put it live)\b", re.I)


def _admin(ctx) -> None:
    if not ctx.user or not ctx.user.is_admin:
        raise PermissionDenied("Only an administrator can change website pages.")


def _page_ref(page) -> dict:
    return {
        "id": str(page.id),
        "slug": page.slug,
        "title": page.title,
        "status": page.status,
        "preview_path": f"/admin/pages/{page.id}",
    }


def create_page_draft(ctx, arguments: dict) -> dict:
    _admin(ctx)
    page = create_page(
        ctx.db,
        ctx.user,
        title=str(arguments.get("title") or "Untitled page"),
        definition=arguments.get("definition") or {},
        slug=arguments.get("slug"),
        summary=arguments.get("summary"),
    )
    return {"page": _page_ref(page), "status": page.status, "message": "Draft saved. It is not public until an administrator publishes it."}


def update_page_draft(ctx, arguments: dict) -> dict:
    _admin(ctx)
    page = update_page(
        ctx.db,
        ctx.user,
        uuid.UUID(str(arguments["page_id"])),
        {"definition": arguments.get("definition"), "title": arguments.get("title"), "summary": arguments.get("summary")},
    )
    return {"page": _page_ref(page), "message": "Draft updated. The live page is unchanged until you publish."}


def get_page_preview(ctx, arguments: dict) -> dict:
    _admin(ctx)
    page = get_page(ctx.db, uuid.UUID(str(arguments["page_id"])))
    payload = page_admin_dict(ctx.db, page)
    return {"page": _page_ref(page), "preview": payload["resolved_draft"]}


def publish_page_tool(ctx, arguments: dict) -> dict:
    _admin(ctx)
    if not arguments.get("confirm"):
        return {"error": "Publishing requires confirm=true and an explicit request from the administrator."}
    if not _PUBLISH.search(ctx.user_message or ""):
        return {"error": "The administrator did not explicitly ask to publish. The draft was left unpublished."}
    page = publish_page(ctx.db, ctx.user, uuid.UUID(str(arguments["page_id"])), confirm=True)
    return {"page": _page_ref(page), "message": "The page is now public."}


def unpublish_page_tool(ctx, arguments: dict) -> dict:
    _admin(ctx)
    page = unpublish_page(ctx.db, ctx.user, uuid.UUID(str(arguments["page_id"])))
    return {"page": _page_ref(page), "message": "The page is no longer public."}
