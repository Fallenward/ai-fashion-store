import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppError, NotFound
from app.core.money import money, q
from app.models import Cart, CartItem, Product, ProductImage, ProductVariant, User, Wishlist, WishlistItem
from app.services.serializers import primary_image, variant_price


def _cart_query():
    return select(Cart).options(
        selectinload(Cart.items)
        .selectinload(CartItem.variant)
        .selectinload(ProductVariant.inventory),
        selectinload(Cart.items)
        .selectinload(CartItem.variant)
        .selectinload(ProductVariant.product)
        .selectinload(Product.images),
    )


def get_cart(db: Session, user: User | None, guest_token: str | None, create: bool = True) -> Cart | None:
    if user is not None:
        cart = db.scalar(_cart_query().where(Cart.user_id == user.id))
        if cart is None and create:
            cart = Cart(user_id=user.id)
            db.add(cart)
            db.commit()
            cart = db.scalar(_cart_query().where(Cart.id == cart.id))
        return cart
    if not guest_token:
        if create:
            raise AppError("A cart token is required.", 400)
        return None
    cart = db.scalar(_cart_query().where(Cart.guest_token == guest_token))
    if cart is None and create:
        cart = Cart(guest_token=guest_token)
        db.add(cart)
        db.commit()
        cart = db.scalar(_cart_query().where(Cart.id == cart.id))
    return cart


def serialize_cart(cart: Cart | None) -> dict:
    items = []
    subtotal = q(0)
    count = 0
    if cart is not None:
        for item in cart.items:
            variant = item.variant
            product = variant.product
            unit = variant_price(variant)
            line = q(unit * item.quantity)
            subtotal += line
            count += item.quantity
            quantity = variant.inventory.quantity if variant.inventory else 0
            items.append(
                {
                    "id": str(item.id),
                    "quantity": item.quantity,
                    "unit_price": money(unit),
                    "line_total": money(line),
                    "available": quantity,
                    "purchasable": product.is_active and variant.is_active and quantity >= item.quantity,
                    "variant": {
                        "id": str(variant.id),
                        "sku": variant.sku,
                        "size": variant.size,
                        "color": variant.color,
                        "color_hex": variant.color_hex,
                    },
                    "product": {
                        "id": str(product.id),
                        "slug": product.slug,
                        "name": product.name,
                        "brand": product.brand,
                        "image": primary_image(product),
                        "url": f"/products/{product.slug}",
                        "is_active": product.is_active,
                    },
                }
            )
    return {
        "id": str(cart.id) if cart else None,
        "items": items,
        "subtotal": money(subtotal),
        "item_count": count,
    }


def _variant(db: Session, variant_id: uuid.UUID) -> ProductVariant:
    variant = db.scalar(
        select(ProductVariant)
        .options(selectinload(ProductVariant.inventory), selectinload(ProductVariant.product))
        .where(ProductVariant.id == variant_id)
    )
    if variant is None or not variant.is_active or not variant.product.is_active:
        raise NotFound("That option is no longer available.")
    return variant


def _clamp_quantity(quantity: int, available: int) -> int:
    if quantity < 1:
        raise AppError("Quantity must be at least 1.")
    if available < 1:
        raise AppError("That option is out of stock.")
    if quantity > available:
        raise AppError(f"Only {available} left in that size and color.")
    return min(quantity, 10)


def add_item(db: Session, user: User | None, guest_token: str | None, variant_id: uuid.UUID, quantity: int) -> dict:
    cart = get_cart(db, user, guest_token, create=True)
    assert cart is not None
    variant = _variant(db, variant_id)
    available = variant.inventory.quantity if variant.inventory else 0
    existing = next((item for item in cart.items if item.variant_id == variant.id), None)
    desired = quantity + (existing.quantity if existing else 0)
    desired = _clamp_quantity(desired, available)
    if existing:
        existing.quantity = desired
    else:
        db.add(CartItem(cart_id=cart.id, variant_id=variant.id, quantity=desired))
    db.commit()
    db.expire_all()
    return serialize_cart(get_cart(db, user, guest_token, create=False))


def update_item(db: Session, user: User | None, guest_token: str | None, item_id: uuid.UUID, quantity: int) -> dict:
    cart = get_cart(db, user, guest_token, create=False)
    if cart is None:
        raise NotFound("Cart not found.")
    item = next((entry for entry in cart.items if entry.id == item_id), None)
    if item is None:
        raise NotFound("That item is not in your cart.")
    available = item.variant.inventory.quantity if item.variant.inventory else 0
    item.quantity = _clamp_quantity(quantity, available)
    db.commit()
    db.expire_all()
    return serialize_cart(get_cart(db, user, guest_token, create=False))


def remove_item(db: Session, user: User | None, guest_token: str | None, item_id: uuid.UUID) -> dict:
    cart = get_cart(db, user, guest_token, create=False)
    if cart is None:
        raise NotFound("Cart not found.")
    item = next((entry for entry in cart.items if entry.id == item_id), None)
    if item is None:
        raise NotFound("That item is not in your cart.")
    db.delete(item)
    db.commit()
    db.expire_all()
    return serialize_cart(get_cart(db, user, guest_token, create=False))


def merge_guest_cart(db: Session, user: User, guest_token: str | None) -> None:
    if not guest_token:
        return
    guest = db.scalar(_cart_query().where(Cart.guest_token == guest_token))
    if guest is None:
        return
    user_cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if user_cart is None:
        guest.user_id = user.id
        guest.guest_token = None
        db.commit()
        return
    for item in list(guest.items):
        try:
            add_item(db, user, None, item.variant_id, item.quantity)
        except AppError:
            continue
    db.delete(guest)
    db.commit()


def _wishlist(db: Session, user: User) -> Wishlist:
    wishlist = db.scalar(
        select(Wishlist)
        .options(selectinload(Wishlist.items).selectinload(WishlistItem.product).selectinload(Product.images),
                 selectinload(Wishlist.items).selectinload(WishlistItem.product).selectinload(Product.category),
                 selectinload(Wishlist.items).selectinload(WishlistItem.product).selectinload(Product.variants).selectinload(ProductVariant.inventory))
        .where(Wishlist.user_id == user.id)
    )
    if wishlist is None:
        wishlist = Wishlist(user_id=user.id)
        db.add(wishlist)
        db.commit()
        db.refresh(wishlist)
        wishlist.items = []
    return wishlist


def list_wishlist(db: Session, user: User) -> list[dict]:
    from app.services.serializers import product_card

    wishlist = _wishlist(db, user)
    cards = []
    for item in wishlist.items:
        if item.product and item.product.is_active:
            cards.append({**product_card(item.product), "wishlist_item_id": str(item.id)})
    return cards


def add_wishlist(db: Session, user: User, product_id: uuid.UUID) -> list[dict]:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFound("Product not found.")
    wishlist = _wishlist(db, user)
    if not any(item.product_id == product.id for item in wishlist.items):
        db.add(WishlistItem(wishlist_id=wishlist.id, product_id=product.id))
        db.commit()
        db.expire_all()
    return list_wishlist(db, user)


def remove_wishlist(db: Session, user: User, product_id: uuid.UUID) -> list[dict]:
    wishlist = _wishlist(db, user)
    item = next((entry for entry in wishlist.items if entry.product_id == product_id), None)
    if item is not None:
        db.delete(item)
        db.commit()
        db.expire_all()
    return list_wishlist(db, user)
