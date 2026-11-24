from decimal import Decimal

from app.core.money import money, q
from app.models import Address, Order, Product, ProductVariant, User


def variant_price(variant: ProductVariant) -> Decimal:
    return q(variant.price if variant.price is not None else variant.product.price)


def primary_image(product: Product) -> str | None:
    images = sorted(product.images, key=lambda image: (not image.is_primary, image.sort_order))
    return images[0].url if images else None


def active_variants(product: Product) -> list[ProductVariant]:
    return [variant for variant in product.variants if variant.is_active]


def product_card(product: Product) -> dict:
    variants = active_variants(product)
    colors: list[str] = []
    sizes: list[str] = []
    for variant in variants:
        if variant.color not in colors:
            colors.append(variant.color)
        if variant.size not in sizes:
            sizes.append(variant.size)
    in_stock = any(variant.inventory and variant.inventory.quantity > 0 for variant in variants)
    compare = product.compare_at_price
    price = q(product.price)
    return {
        "id": str(product.id),
        "slug": product.slug,
        "name": product.name,
        "brand": product.brand,
        "price": money(price),
        "compare_at_price": money(compare) if compare and compare > price else None,
        "currency": product.currency,
        "category": {"id": str(product.category.id), "slug": product.category.slug, "name": product.category.name},
        "image": primary_image(product),
        "colors": colors,
        "sizes": sizes,
        "in_stock": in_stock,
        "is_new": product.is_new,
        "is_bestseller": product.is_bestseller,
        "is_featured": product.is_featured,
        "is_trending": product.is_trending,
        "url": f"/products/{product.slug}",
    }


def product_detail(product: Product) -> dict:
    card = product_card(product)
    images = sorted(product.images, key=lambda image: image.sort_order)
    variants = []
    for variant in active_variants(product):
        quantity = variant.inventory.quantity if variant.inventory else 0
        threshold = variant.inventory.low_stock_threshold if variant.inventory else 5
        variants.append(
            {
                "id": str(variant.id),
                "sku": variant.sku,
                "size": variant.size,
                "color": variant.color,
                "color_hex": variant.color_hex,
                "price": money(variant_price(variant)),
                "quantity": quantity,
                "low_stock": quantity <= threshold,
                "in_stock": quantity > 0,
            }
        )
    card.update(
        {
            "description": product.description,
            "material": product.material,
            "care": product.care,
            "images": [{"id": str(image.id), "url": image.url, "alt": image.alt, "is_primary": image.is_primary} for image in images],
            "variants": variants,
            "is_active": product.is_active,
        }
    )
    return card


def public_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role_name,
        "phone": user.profile.phone if user.profile else None,
    }


def address_dict(address: Address) -> dict:
    return {
        "id": str(address.id),
        "label": address.label,
        "full_name": address.full_name,
        "line1": address.line1,
        "line2": address.line2,
        "city": address.city,
        "region": address.region,
        "postal_code": address.postal_code,
        "country": address.country,
        "phone": address.phone,
        "is_default": address.is_default,
    }


def order_summary(order: Order) -> dict:
    return {
        "id": str(order.id),
        "number": order.number,
        "status": order.status,
        "email": order.email,
        "subtotal": money(order.subtotal),
        "shipping_fee": money(order.shipping_fee),
        "discount": money(order.discount),
        "total": money(order.total),
        "promo_code": order.promo_code,
        "currency": order.currency,
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "id": str(item.id),
                "product_name": item.product_name,
                "sku": item.sku,
                "size": item.size,
                "color": item.color,
                "unit_price": money(item.unit_price),
                "quantity": item.quantity,
                "image_url": item.image_url,
                "variant_id": str(item.variant_id) if item.variant_id else None,
            }
            for item in order.items
        ],
        "shipping_address": order.shipping_address,
        "payment": None
        if order.payment is None
        else {
            "provider": order.payment.provider,
            "status": order.payment.status,
            "amount": money(order.payment.amount),
        },
    }
