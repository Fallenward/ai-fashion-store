import uuid
from decimal import Decimal, InvalidOperation

from app.core.exceptions import NotFound
from app.repositories.product_repository import ProductSearch, get_product, search_products
from app.services.recommendation import recommend_products, related_products
from app.services.serializers import product_card, product_detail


def _decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def search_products_tool(ctx, arguments: dict) -> dict:
    products, total = search_products(
        ctx.db,
        ProductSearch(
            query=arguments.get("query"),
            category=arguments.get("category"),
            size=arguments.get("size"),
            color=arguments.get("color"),
            brand=arguments.get("brand"),
            min_price=_decimal(arguments.get("min_price")),
            max_price=_decimal(arguments.get("max_price")),
            in_stock=True if arguments.get("in_stock") is not False else None,
            sort=arguments.get("sort") or "popularity",
            page=int(arguments.get("page") or 1),
            page_size=min(int(arguments.get("limit") or 6), 8),
        ),
    )
    return {
        "total": total,
        "products": [product_card(product) for product in products],
        "note": "Prices and stock in this list are live.",
    }


def get_product_details(ctx, arguments: dict) -> dict:
    product = None
    if arguments.get("product_id"):
        product = get_product(ctx.db, uuid.UUID(str(arguments["product_id"])))
    elif arguments.get("slug"):
        from app.repositories.product_repository import get_product_by_slug

        product = get_product_by_slug(ctx.db, str(arguments["slug"]))
    if product is None:
        raise NotFound("Product not found.")
    return {"product": product_detail(product)}


def get_product_inventory(ctx, arguments: dict) -> dict:
    detail = get_product_details(ctx, arguments)["product"]
    return {
        "product_id": detail["id"],
        "name": detail["name"],
        "variants": [
            {"sku": variant["sku"], "size": variant["size"], "color": variant["color"], "quantity": variant["quantity"], "in_stock": variant["in_stock"]}
            for variant in detail["variants"]
        ],
    }


def compare_products(ctx, arguments: dict) -> dict:
    ids = []
    for raw in arguments.get("product_ids") or []:
        try:
            ids.append(uuid.UUID(str(raw)))
        except ValueError:
            continue
    cards = []
    for product_id in ids[:4]:
        product = get_product(ctx.db, product_id)
        if product:
            detail = product_detail(product)
            cards.append(
                {
                    **product_card(product),
                    "material": detail["material"],
                    "care": detail["care"],
                    "variants": detail["variants"],
                }
            )
    return {"products": cards}


def get_related_products(ctx, arguments: dict) -> dict:
    product_id = uuid.UUID(str(arguments["product_id"]))
    return {"products": related_products(ctx.db, product_id)}


def recommend(ctx, arguments: dict) -> dict:
    preferences = arguments.get("preferences") if isinstance(arguments.get("preferences"), dict) else {}
    for key in ("colors", "categories", "brands", "sizes", "keywords"):
        if arguments.get(key):
            preferences[key] = arguments[key]
    return recommend_products(
        ctx.db,
        user=ctx.user,
        preferences=preferences,
        budget=_decimal(arguments.get("budget")),
        occasion=arguments.get("occasion"),
        limit=min(int(arguments.get("limit") or 4), 6),
    )
