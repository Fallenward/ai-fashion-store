import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFound, PermissionDenied, Unauthorized
from app.models import Order, User
from app.services.account_service import get_style, save_style
from app.services.cart_service import list_wishlist
from app.services.serializers import order_summary


def _subject(ctx, requested_id: str | None) -> User:
    if ctx.user is None:
        raise Unauthorized("Sign in so I can use your account.")
    if requested_id and str(ctx.user.id) != str(requested_id):
        if not ctx.user.is_admin:
            raise PermissionDenied("You can only access your own account.")
        user = ctx.db.scalar(select(User).options(selectinload(User.role)).where(User.id == uuid.UUID(str(requested_id))))
        if user is None:
            raise NotFound("Customer not found.")
        return user
    return ctx.user


def get_customer_style_profile(ctx, arguments: dict) -> dict:
    user = _subject(ctx, arguments.get("customer_id"))
    return get_style(ctx.db, user)


def update_customer_style_profile(ctx, arguments: dict) -> dict:
    user = _subject(ctx, None)
    if user.is_admin and arguments.get("customer_id") and str(arguments["customer_id"]) != str(user.id):
        raise PermissionDenied("Style profiles are updated by the customer who owns them.")
    payload = {key: arguments.get(key) for key in ("preferred_sizes", "favorite_colors", "favorite_categories", "preferred_brands", "style_keywords", "budget_min", "budget_max", "notes", "opt_out") if key in arguments}
    return save_style(ctx.db, user, payload)


def get_customer_wishlist(ctx, arguments: dict) -> dict:
    user = _subject(ctx, arguments.get("customer_id"))
    return {"products": list_wishlist(ctx.db, user)}


def get_customer_order_history(ctx, arguments: dict) -> dict:
    user = _subject(ctx, arguments.get("customer_id"))
    orders = ctx.db.scalars(
        select(Order).options(selectinload(Order.items), selectinload(Order.payment)).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(8)
    ).all()
    return {
        "orders": [
            {
                "number": order.number,
                "status": order.status,
                "total": order_summary(order)["total"],
                "created_at": order.created_at.isoformat(),
                "items": [f"{item.product_name} ({item.size}/{item.color}) x{item.quantity}" for item in order.items],
            }
            for order in orders
        ]
    }
