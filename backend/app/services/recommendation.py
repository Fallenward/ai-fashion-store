import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.money import q
from app.models import User
from app.repositories.product_repository import ProductSearch, get_product, search_products
from app.services.account_service import style_for_agent
from app.services.serializers import product_card

OCCASION_SLOTS = {
    "casual dinner": ["tops", "trousers", "shoes", "outerwear"],
    "dinner": ["dresses", "shoes", "accessories", "outerwear"],
    "office": ["tops", "trousers", "outerwear", "shoes"],
    "work": ["tops", "trousers", "outerwear", "shoes"],
    "weekend": ["tops", "denim", "shoes", "accessories"],
    "summer": ["dresses", "tops", "shoes", "accessories"],
    "winter": ["outerwear", "knitwear", "trousers", "shoes"],
    "date": ["dresses", "shoes", "accessories", "knitwear"],
}

NEUTRALS = {"black", "white", "ivory", "cream", "beige", "sand", "camel", "charcoal", "brown", "navy", "gray"}


def _budget(explicit: Decimal | None, profile: dict | None) -> Decimal | None:
    if explicit is not None:
        return q(explicit)
    if profile and not profile.get("opted_out") and profile.get("budget_max"):
        return q(profile["budget_max"])
    return None


def _prefs(profile: dict | None, preferences: dict | None) -> dict:
    merged = {
        "colors": [],
        "categories": [],
        "brands": [],
        "sizes": [],
        "keywords": [],
    }
    if profile and not profile.get("opted_out"):
        merged["colors"] = [c.lower() for c in profile.get("favorite_colors") or []]
        merged["categories"] = [c.lower() for c in profile.get("favorite_categories") or []]
        merged["brands"] = [c.lower() for c in profile.get("preferred_brands") or []]
        merged["sizes"] = profile.get("preferred_sizes") or []
        merged["keywords"] = [c.lower() for c in profile.get("style_keywords") or []]
    if preferences:
        for key, source in (
            ("colors", "colors"),
            ("categories", "categories"),
            ("brands", "brands"),
            ("sizes", "sizes"),
            ("keywords", "keywords"),
        ):
            values = preferences.get(source) or preferences.get(key)
            if values:
                merged[key] = [str(value).lower() for value in values]
    return merged


def _score(product, prefs: dict) -> float:
    score = product.popularity / 50
    colors = {variant.color.lower() for variant in product.variants if variant.inventory and variant.inventory.quantity > 0}
    if prefs["colors"] and colors.intersection(prefs["colors"]):
        score += 4
    elif colors.intersection(NEUTRALS):
        score += 1
    if product.brand.lower() in prefs["brands"]:
        score += 3
    if product.category.slug in prefs["categories"] or product.category.name.lower() in prefs["categories"]:
        score += 3
    text = f"{product.name} {product.description} {product.material or ''}".lower()
    for keyword in prefs["keywords"]:
        if keyword and keyword in text:
            score += 1
    if product.is_bestseller:
        score += 1
    return score


def _in_stock_cards(products, limit: int, prefs: dict) -> list[dict]:
    ranked = sorted(products, key=lambda product: _score(product, prefs), reverse=True)
    cards = []
    for product in ranked:
        card = product_card(product)
        if not card["in_stock"]:
            continue
        card["why"] = _why(product, prefs)
        cards.append(card)
        if len(cards) >= limit:
            break
    return cards


def _why(product, prefs: dict) -> str:
    reasons = []
    if product.brand.lower() in prefs["brands"]:
        reasons.append(f"brand {product.brand} is one you saved")
    colors = [variant.color for variant in product.variants if variant.inventory and variant.inventory.quantity > 0]
    if prefs["colors"] and any(color.lower() in prefs["colors"] for color in colors):
        reasons.append("it comes in a color you prefer")
    if not reasons:
        reasons.append("it is in stock now")
    return f"{product.name}: " + ", ".join(reasons) + "."


def recommend_products(
    db: Session,
    *,
    user: User | None = None,
    preferences: dict | None = None,
    budget: Decimal | None = None,
    occasion: str | None = None,
    anchor_product_id: uuid.UUID | None = None,
    limit: int = 4,
) -> dict:
    profile = style_for_agent(db, user)
    prefs = _prefs(profile, preferences)
    max_price = _budget(budget, profile)
    occasion_key = (occasion or "").strip().lower() or None
    slots = OCCASION_SLOTS.get(occasion_key or "", [])
    chosen = []
    seen: set[uuid.UUID] = set()
    if anchor_product_id:
        seen.add(anchor_product_id)
    if slots:
        for slug in slots:
            products, _ = search_products(
                db,
                ProductSearch(category=slug, max_price=max_price, in_stock=True, page_size=20, sort="popularity"),
            )
            products = [product for product in products if product.id not in seen]
            cards = _in_stock_cards(products, 1, prefs)
            if cards:
                chosen.append(cards[0])
                seen.add(uuid.UUID(cards[0]["id"]))
    if len(chosen) < limit:
        products, _ = search_products(
            db,
            ProductSearch(max_price=max_price, in_stock=True, page_size=30, sort="popularity", query=None),
        )
        extra = _in_stock_cards([product for product in products if product.id not in seen], limit - len(chosen), prefs)
        chosen.extend(extra)
    explanation = _explain(occasion_key, chosen, max_price)
    return {"products": chosen[:limit], "explanation": explanation, "occasion": occasion_key, "budget": str(max_price) if max_price is not None else None}


def _explain(occasion: str | None, products: list[dict], budget: Decimal | None) -> str:
    if not products:
        limit = f" under ${budget}" if budget is not None else ""
        return f"Nothing currently in stock matches that request{limit}. Try another color, size, or a higher budget."
    names = [f"{item['name']} ({item['price']})" for item in products]
    budget_text = f" Budget ceiling: ${budget}." if budget is not None else ""
    if occasion:
        return f"For {occasion}, these pieces are in stock and can be worn together: {'; '.join(names)}.{budget_text}"
    return f"These in-stock pieces match the preferences on file: {'; '.join(names)}.{budget_text}"


def styling_for_product(db: Session, slug: str) -> dict:
    from app.repositories.product_repository import get_product_by_slug

    product = get_product_by_slug(db, slug)
    if product is None:
        return {"items": [], "explanation": "This piece is not in the catalog."}
    occasion = {
        "dresses": "dinner",
        "outerwear": "winter",
        "denim": "weekend",
        "shoes": "casual dinner",
        "knitwear": "office",
    }.get(product.category.slug, "casual dinner")
    colors = [variant.color for variant in product.variants]
    result = recommend_products(
        db,
        preferences={"colors": colors[:2], "keywords": [product.material or ""]},
        occasion=occasion,
        anchor_product_id=product.id,
        limit=3,
    )
    return {"items": result["products"], "explanation": result["explanation"], "occasion": occasion}


def related_products(db: Session, product_id: uuid.UUID, limit: int = 4) -> list[dict]:
    product = get_product(db, product_id)
    if product is None:
        return []
    products, _ = search_products(
        db, ProductSearch(category=product.category.slug, in_stock=True, page_size=8, sort="popularity")
    )
    cards = []
    for item in products:
        if item.id == product.id:
            continue
        cards.append(product_card(item))
        if len(cards) >= limit:
            break
    return cards
