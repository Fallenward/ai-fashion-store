import logging
import secrets
import uuid
from decimal import Decimal

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFound
from app.core.money import money, q
from app.models import Inventory, Order, OrderItem, Payment, ProductVariant, PromoCode, User
from app.services.cart_service import get_cart, serialize_cart
from app.services.serializers import address_dict, order_summary

logger = logging.getLogger(__name__)
PAID_STATUSES = {"paid", "processing", "shipped", "delivered"}


def _promo(db: Session, code: str | None, subtotal: Decimal) -> tuple[Decimal, str | None]:
    if not code:
        return q(0), None
    promo = db.scalar(select(PromoCode).where(PromoCode.code == code.strip().upper()))
    if promo is None or not promo.is_active:
        raise AppError("That promo code is not active.")
    if subtotal < q(promo.min_subtotal):
        raise AppError(f"That code requires a subtotal of {money(promo.min_subtotal)}.")
    if promo.percent_off:
        discount = q(subtotal * Decimal(promo.percent_off) / Decimal(100))
    else:
        discount = q(promo.amount_off or 0)
    if discount > subtotal:
        discount = subtotal
    return discount, promo.code


def _shipping(subtotal: Decimal) -> Decimal:
    settings = get_settings()
    if subtotal >= q(settings.free_shipping_over):
        return q(0)
    return q(settings.shipping_flat)


def _lines(db: Session, user: User) -> tuple[list, Decimal]:
    cart = get_cart(db, user, None, create=False)
    payload = serialize_cart(cart)
    if not payload["items"]:
        raise AppError("Your cart is empty.")
    blocked = [item["product"]["name"] for item in payload["items"] if not item["purchasable"]]
    if blocked:
        raise AppError("Remove unavailable items before checkout: " + ", ".join(blocked))
    return payload["items"], q(payload["subtotal"])


def quote_cart(db: Session, user: User, promo_code: str | None) -> dict:
    _items, subtotal = _lines(db, user)
    discount, applied = _promo(db, promo_code, subtotal)
    shipping = _shipping(subtotal)
    total = q(subtotal - discount + shipping)
    settings = get_settings()
    remaining = q(settings.free_shipping_over - subtotal)
    return {
        "subtotal": money(subtotal),
        "discount": money(discount),
        "shipping_fee": money(shipping),
        "total": money(total),
        "promo_code": applied,
        "free_shipping_remaining": money(remaining) if remaining > 0 else None,
        "payment_mode": "stripe" if settings.stripe_enabled else "mock",
    }


def _store_address(db: Session, user: User, payload: dict, save: bool):
    from app.models import Address

    if payload.get("address_id"):
        address = db.get(Address, uuid.UUID(str(payload["address_id"])))
        if address is None or address.user_id != user.id:
            raise NotFound("Address not found.")
        return address_dict(address)
    required = ["full_name", "line1", "city", "region", "postal_code", "country"]
    if any(not payload.get(field) for field in required):
        raise AppError("A complete shipping address is required.")
    snapshot = {
        "full_name": payload["full_name"].strip(),
        "line1": payload["line1"].strip(),
        "line2": (payload.get("line2") or "").strip() or None,
        "city": payload["city"].strip(),
        "region": payload["region"].strip(),
        "postal_code": payload["postal_code"].strip(),
        "country": payload["country"].strip(),
        "phone": (payload.get("phone") or "").strip() or None,
    }
    if save:
        if payload.get("is_default"):
            for existing in user.addresses:
                existing.is_default = False
        db.add(
            Address(
                user_id=user.id,
                label=payload.get("label") or "Shipping",
                is_default=bool(payload.get("is_default")),
                **snapshot,
            )
        )
    return snapshot


def _order_number(db: Session) -> str:
    for _ in range(5):
        number = "AT-" + secrets.token_hex(4).upper()
        if db.scalar(select(Order.id).where(Order.number == number)) is None:
            return number
    raise AppError("Could not allocate an order number.", 500)


def create_checkout(db: Session, user: User, payload: dict) -> dict:
    items, subtotal = _lines(db, user)
    discount, applied = _promo(db, payload.get("promo_code"), subtotal)
    shipping = _shipping(subtotal)
    total = q(subtotal - discount + shipping)
    address = _store_address(db, user, payload, bool(payload.get("save_address")))
    cart = get_cart(db, user, None, create=False)
    assert cart is not None
    order = Order(
        user_id=user.id,
        number=_order_number(db),
        status="pending",
        email=user.email,
        shipping_address=address,
        subtotal=subtotal,
        shipping_fee=shipping,
        discount=discount,
        total=total,
        promo_code=applied,
    )
    db.add(order)
    db.flush()
    for line in items:
        variant = db.get(ProductVariant, uuid.UUID(line["variant"]["id"]))
        if variant is None or variant.inventory is None:
            raise AppError("A cart item is no longer available.")
        if variant.inventory.quantity < line["quantity"]:
            raise AppError(f"Only {variant.inventory.quantity} left of {line['product']['name']}.")
        db.add(
            OrderItem(
                order_id=order.id,
                variant_id=variant.id,
                product_name=line["product"]["name"],
                sku=line["variant"]["sku"],
                size=line["variant"]["size"],
                color=line["variant"]["color"],
                unit_price=q(line["unit_price"]),
                quantity=line["quantity"],
                image_url=line["product"]["image"],
            )
        )
    settings = get_settings()
    provider = "stripe" if settings.stripe_enabled else "mock"
    payment = Payment(order_id=order.id, provider=provider, status="pending", amount=total)
    db.add(payment)
    db.flush()
    checkout_url = None
    if provider == "stripe":
        stripe.api_key = settings.stripe_secret_key
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                customer_email=user.email,
                client_reference_id=str(order.id),
                success_url=f"{settings.public_app_url}/orders/{order.id}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.public_app_url}/checkout?cancelled=1",
                metadata={"order_id": str(order.id)},
                line_items=[
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": int(q(total) * 100),
                            "product_data": {"name": f"Atelier order {order.number}"},
                        },
                    }
                ],
            )
        except Exception as exc:
            logger.exception("Stripe session creation failed")
            db.rollback()
            raise AppError("Payment could not be started. Nothing was charged and your cart is unchanged.", 502) from exc
        payment.stripe_session_id = session.id
        checkout_url = session.url
    for item in list(cart.items):
        db.delete(item)
    db.commit()
    if checkout_url:
        return {"mode": "stripe", "url": checkout_url, "order_id": str(order.id), "order_number": order.number}
    return {
        "mode": "mock",
        "order_id": str(order.id),
        "order_number": order.number,
        "message": "Development mock checkout. No card is charged.",
    }


def _lock_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payment))
        .where(Order.id == order_id)
        .with_for_update()
    )
    if order is None:
        raise NotFound("Order not found.")
    return order


def finalize_payment(db: Session, order_id: uuid.UUID) -> Order:
    order = _lock_order(db, order_id)
    if order.payment and order.payment.status == "paid":
        db.commit()
        return order
    if order.status not in {"pending", "paid"}:
        raise AppError("This order can no longer be paid.")
    for item in order.items:
        if item.variant_id is None:
            raise AppError(f"{item.product_name} is no longer available.")
        inventory = db.scalar(
            select(Inventory).where(Inventory.variant_id == item.variant_id).with_for_update()
        )
        if inventory is None or inventory.quantity < item.quantity:
            available = inventory.quantity if inventory else 0
            raise AppError(f"Only {available} left of {item.product_name} ({item.size} / {item.color}).")
        inventory.quantity -= item.quantity
    order.status = "paid"
    if order.payment:
        order.payment.status = "paid"
    db.commit()
    return order


def mock_pay(db: Session, user: User, order_id: uuid.UUID) -> dict:
    if get_settings().stripe_enabled:
        raise AppError("Mock checkout is disabled because Stripe is configured.", 400)
    order = db.scalar(select(Order).options(selectinload(Order.payment)).where(Order.id == order_id))
    if order is None or order.user_id != user.id:
        raise NotFound("Order not found.")
    if order.payment is None or order.payment.provider != "mock":
        raise AppError("This order is not a development mock payment.")
    if order.status != "pending":
        raise AppError("This order is not awaiting payment.")
    finalize_payment(db, order.id)
    return order_summary(get_order(db, user, order.id))


def handle_stripe_webhook(db: Session, payload: bytes, signature: str | None) -> dict:
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise AppError("Stripe webhook secret is not configured.", 400)
    if not signature:
        raise AppError("Missing Stripe signature.", 400)
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError as exc:
        raise AppError("Invalid Stripe signature.", 400) from exc
    except ValueError as exc:
        raise AppError("Invalid Stripe payload.", 400) from exc
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("payment_status") != "paid":
            return {"received": True}
        raw_id = (session.get("metadata") or {}).get("order_id") or session.get("client_reference_id")
        if not raw_id:
            logger.warning("Stripe session %s had no order id", session.get("id"))
            return {"received": True}
        order = db.get(Order, uuid.UUID(raw_id))
        if order is None or order.payment is None:
            return {"received": True}
        if order.payment.stripe_session_id and order.payment.stripe_session_id != session.get("id"):
            logger.warning("Stripe session mismatch for order %s", order.id)
            return {"received": True}
        intent = session.get("payment_intent")
        if intent and not order.payment.stripe_payment_intent:
            order.payment.stripe_payment_intent = intent
            db.commit()
        try:
            finalize_payment(db, order.id)
        except AppError:
            logger.exception("Payment captured but inventory could not be reserved for order %s", order.id)
            failed = db.get(Order, order.id)
            if failed and failed.status == "pending":
                failed.status = "cancelled"
                if failed.payment:
                    failed.payment.status = "failed"
                db.commit()
    return {"received": True}


def get_order(db: Session, user: User, order_id: uuid.UUID) -> Order:
    order = db.scalar(
        select(Order).options(selectinload(Order.items), selectinload(Order.payment)).where(Order.id == order_id)
    )
    if order is None or (not user.is_admin and order.user_id != user.id):
        raise NotFound("Order not found.")
    return order


def list_orders(db: Session, user: User) -> list[dict]:
    orders = db.scalars(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payment))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    ).all()
    return [order_summary(order) for order in orders]


def refund_order(db: Session, order_id: uuid.UUID) -> dict:
    order = _lock_order(db, order_id)
    if order.status not in PAID_STATUSES:
        raise AppError("Only paid orders can be refunded.")
    settings = get_settings()
    if (
        order.payment
        and order.payment.provider == "stripe"
        and order.payment.stripe_payment_intent
        and settings.stripe_enabled
    ):
        stripe.api_key = settings.stripe_secret_key
        stripe.Refund.create(payment_intent=order.payment.stripe_payment_intent)
    for item in order.items:
        if item.variant_id is None:
            continue
        inventory = db.scalar(select(Inventory).where(Inventory.variant_id == item.variant_id).with_for_update())
        if inventory is not None:
            inventory.quantity += item.quantity
    order.status = "refunded"
    if order.payment:
        order.payment.status = "refunded"
    db.commit()
    refreshed = db.scalar(
        select(Order).options(selectinload(Order.items), selectinload(Order.payment)).where(Order.id == order_id)
    )
    return order_summary(refreshed)


def update_order_status(db: Session, order_id: uuid.UUID, status: str) -> dict:
    order = _lock_order(db, order_id)
    allowed = {
        "pending": {"cancelled"},
        "paid": {"processing", "shipped", "delivered", "cancelled", "refunded"},
        "processing": {"shipped", "delivered", "cancelled", "refunded"},
        "shipped": {"delivered", "refunded"},
        "delivered": {"refunded"},
    }
    if status not in allowed.get(order.status, set()):
        raise AppError(f"Cannot change an order from {order.status} to {status}.")
    if status in {"cancelled", "refunded"} and order.status in PAID_STATUSES:
        db.commit()
        return refund_order(db, order_id)
    order.status = status
    if status == "cancelled" and order.payment and order.payment.status == "pending":
        order.payment.status = "failed"
    db.commit()
    refreshed = db.scalar(
        select(Order).options(selectinload(Order.items), selectinload(Order.payment)).where(Order.id == order_id)
    )
    return order_summary(refreshed)
