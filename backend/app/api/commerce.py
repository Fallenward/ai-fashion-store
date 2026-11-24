import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import cart_token, get_current_user, get_optional_user
from app.models import User
from app.services.cart_service import add_item, add_wishlist, get_cart, list_wishlist, remove_item, remove_wishlist, serialize_cart, update_item
from app.services.checkout_service import create_checkout, get_order, list_orders, mock_pay, quote_cart
from app.services.serializers import order_summary

router = APIRouter(tags=["commerce"])


class CartAdd(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=10)


class CartUpdate(BaseModel):
    quantity: int = Field(ge=1, le=10)


class WishlistAdd(BaseModel):
    product_id: uuid.UUID


class CheckoutIn(BaseModel):
    address_id: uuid.UUID | None = None
    full_name: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = "United States"
    phone: str | None = None
    label: str | None = None
    save_address: bool = False
    is_default: bool = False
    promo_code: str | None = None


class QuoteIn(BaseModel):
    promo_code: str | None = None


@router.get("/cart")
def read_cart(
    user: User | None = Depends(get_optional_user),
    token: str | None = Depends(cart_token),
    db: Session = Depends(get_db),
):
    return serialize_cart(get_cart(db, user, token, create=bool(user or token)))


@router.post("/cart/items")
def post_item(
    payload: CartAdd,
    user: User | None = Depends(get_optional_user),
    token: str | None = Depends(cart_token),
    db: Session = Depends(get_db),
):
    return add_item(db, user, token, payload.variant_id, payload.quantity)


@router.patch("/cart/items/{item_id}")
def patch_item(
    item_id: uuid.UUID,
    payload: CartUpdate,
    user: User | None = Depends(get_optional_user),
    token: str | None = Depends(cart_token),
    db: Session = Depends(get_db),
):
    return update_item(db, user, token, item_id, payload.quantity)


@router.delete("/cart/items/{item_id}")
def delete_item(
    item_id: uuid.UUID,
    user: User | None = Depends(get_optional_user),
    token: str | None = Depends(cart_token),
    db: Session = Depends(get_db),
):
    return remove_item(db, user, token, item_id)


@router.get("/wishlist")
def wishlist(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": list_wishlist(db, user)}


@router.post("/wishlist")
def wishlist_add(payload: WishlistAdd, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": add_wishlist(db, user, payload.product_id)}


@router.delete("/wishlist/{product_id}")
def wishlist_remove(product_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": remove_wishlist(db, user, product_id)}


@router.post("/checkout/quote")
def quote(payload: QuoteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return quote_cart(db, user, payload.promo_code)


@router.post("/checkout")
def checkout(payload: CheckoutIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_checkout(db, user, payload.model_dump())


@router.post("/checkout/{order_id}/mock-pay")
def pay_mock(order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return mock_pay(db, user, order_id)


@router.get("/orders")
def orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": list_orders(db, user)}


@router.get("/orders/{order_id}")
def order_detail(order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return order_summary(get_order(db, user, order_id))
