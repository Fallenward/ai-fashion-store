"""Idempotent demo data. Safe to run more than once."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.rag.ingest import ingest_product_catalog, ingest_store_documents
from app.core.database import get_session_factory
from app.core.security import hash_password
from app.models import (
    Address,
    Category,
    CustomerProfile,
    CustomerStyleProfile,
    Inventory,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductImage,
    ProductVariant,
    PromoCode,
    Role,
    User,
)
from app.seed_images import write_svg
from app.services.page_service import create_page, publish_page

CATEGORIES = [
    ("Outerwear", "outerwear", "Coats, jackets, and blazers cut with a quiet shoulder.", 1, "#d9cfc3", "#3d342c", "outer"),
    ("Tops", "tops", "Shirts, knits worn as tops, and the hoodie people actually live in.", 2, "#ece4da", "#1c1917", "top"),
    ("Knitwear", "knitwear", "Sweaters and cardigans in yarns that hold their shape.", 3, "#e7ddd2", "#4a3b32", "knit"),
    ("Dresses", "dresses", "Day dresses and evening slips with an easy line.", 4, "#f3e6ea", "#6d2a38", "dress"),
    ("Trousers", "trousers", "Tailored trousers with room to move.", 5, "#e5e1d8", "#2c2926", "trouser"),
    ("Denim", "denim", "Straight jeans and a jacket that gets better with wear.", 6, "#d5dde6", "#243044", "denim"),
    ("Shoes", "shoes", "Boots and sneakers chosen to finish an outfit.", 7, "#efe6da", "#5c4636", "shoe"),
    ("Accessories", "accessories", "Small pieces: belts, scarves, and jewelry.", 8, "#f6f1ea", "#8a6a32", "accessory"),
]

PRODUCTS = [
    dict(name="Black Oversized Hoodie", brand="Halden", category="tops", price="54.00", compare="68.00", material="Organic cotton fleece", popularity=98, flags={"is_bestseller": True, "is_featured": True, "is_trending": True}, kind="top", bg="#1c1917", ink="#f4efe8", colors=[("Black", "#161513")], sizes=["XS", "S", "M", "L", "XL"], stock={"XL": 2}, description="A heavy black hoodie with a dropped shoulder and a hood that stays put. Oversized without looking sloppy, and priced under sixty dollars."),
    dict(name="Navy Zip Hoodie", brand="Halden", category="tops", price="78.00", material="Cotton blend", popularity=40, kind="top", bg="#1e2a44", ink="#e7e1d6", colors=[("Navy", "#1e2a44")], sizes=["S", "M", "L", "XL"], description="A navy zip hoodie with a cleaner hem. It is not the black oversized one, and it sits above a sixty-dollar budget."),
    dict(name="Ivory Silk Camisole", brand="Lumen", category="tops", price="68.00", material="Silk charmeuse", popularity=70, flags={"is_featured": True, "is_new": True}, kind="top", bg="#f7f1e6", ink="#c2b6a4", colors=[("Ivory", "#f4efe4")], sizes=["XS", "S", "M", "L"], description="A bias-cut ivory camisole with a narrow strap. It layers under blazers and stands alone at dinner."),
    dict(name="White Poplin Shirt", brand="Marlowe", category="tops", price="64.00", material="Cotton poplin", popularity=80, flags={"is_bestseller": True}, kind="top", bg="#fbf7f2", ink="#d9d3cb", colors=[("White", "#f7f7f5")], sizes=["XS", "S", "M", "L", "XL"], description="A crisp white shirt with a soft collar and a slightly long cuff. The everyday piece in the line."),
    dict(name="Striped Breton Tee", brand="Vesper", category="tops", price="42.00", material="Cotton jersey", popularity=60, flags={"is_trending": True}, kind="top", bg="#f3efe8", ink="#243044", colors=[("Navy", "#243044"), ("White", "#f7f7f5")], sizes=["XS", "S", "M", "L"], description="A navy and white striped tee with a boat neck. Easy with denim or tailored trousers."),
    dict(name="Linen Summer Shirt", brand="Sable & Co", category="tops", price="74.00", material="Washed linen", popularity=55, flags={"is_new": True, "is_featured": True}, kind="top", bg="#e7d7c3", ink="#8a6a46", colors=[("Sand", "#cbb89a")], sizes=["S", "M", "L", "XL"], description="A sand linen shirt, cut straight, with a camp collar. It wrinkles on purpose."),
    dict(name="Charcoal Wool Overcoat", brand="Atelier North", category="outerwear", price="240.00", compare="280.00", material="Wool melton", popularity=88, flags={"is_featured": True, "is_bestseller": True}, kind="outer", bg="#2a2928", ink="#b7b1a8", colors=[("Charcoal", "#2c2c2c")], sizes=["S", "M", "L", "XL"], description="A charcoal overcoat with a clean lapel and enough weight for a cold evening. It anchors a winter outfit."),
    dict(name="Sand Trench Coat", brand="Atelier North", category="outerwear", price="198.00", material="Cotton gabardine", popularity=76, flags={"is_trending": True}, kind="outer", bg="#d9c7ae", ink="#6b5340", colors=[("Sand", "#cbb89a")], sizes=["XS", "S", "M", "L"], description="A sand trench with a concealed placket and a belt you can leave off. It works over dresses and denim."),
    dict(name="Olive Field Jacket", brand="Vesper", category="outerwear", price="160.00", material="Cotton twill", popularity=64, kind="outer", bg="#5d6244", ink="#e6e0d4", colors=[("Olive", "#5d6244")], sizes=["S", "M", "L", "XL"], description="An olive field jacket with a four-pocket front. Rugged, but the cloth is soft."),
    dict(name="Relaxed Beige Blazer", brand="Marlowe", category="outerwear", price="175.00", material="Wool blend", popularity=72, flags={"is_new": True}, kind="outer", bg="#e6dccb", ink="#8d775c", colors=[("Beige", "#d9cbb6")], sizes=["XS", "S", "M", "L"], description="A beige blazer with a relaxed shoulder. It is the office layer that still looks right at dinner."),
    dict(name="Cream Cashmere Sweater", brand="Lumen", category="knitwear", price="145.00", material="Cashmere", popularity=84, flags={"is_featured": True, "is_bestseller": True}, kind="knit", bg="#f3ecdf", ink="#e4d5c0", colors=[("Cream", "#f3ecdf")], sizes=["XS", "S", "M", "L"], description="A cream crewneck in light cashmere. Quiet enough to sit next to black trousers or a slip dress."),
    dict(name="Navy Ribbed Cardigan", brand="Halden", category="knitwear", price="98.00", material="Merino wool", popularity=66, flags={"is_trending": True}, kind="knit", bg="#243044", ink="#d5dbe4", colors=[("Navy", "#243044")], sizes=["XS", "S", "M", "L", "XL"], description="A navy ribbed cardigan with horn buttons. It replaces a jacket when the room is warm."),
    dict(name="Black Turtleneck", brand="Sable & Co", category="knitwear", price="72.00", material="Fine merino", popularity=90, flags={"is_bestseller": True}, kind="knit", bg="#161513", ink="#3a3836", colors=[("Black", "#161513")], sizes=["XS", "S", "M", "L", "XL"], description="A close black turtleneck. The simplest layer under a coat or blazer."),
    dict(name="Midnight Slip Dress", brand="Lumen", category="dresses", price="128.00", material="Silk satin", popularity=86, flags={"is_featured": True, "is_trending": True}, kind="dress", bg="#1a1520", ink="#3a2a38", colors=[("Midnight", "#1a1520")], sizes=["XS", "S", "M", "L"], description="A midnight slip dress with a bias skirt. It is the answer to a dinner invitation."),
    dict(name="Floral Day Dress", brand="Vesper", category="dresses", price="96.00", material="Cotton poplin", popularity=58, flags={"is_new": True}, kind="dress", bg="#f6e7ea", ink="#6d2a38", colors=[("Ivory", "#f7f1e8")], sizes=["XS", "S", "M", "L", "XL"], stock={"XL": 0}, description="A small-scale floral dress on ivory cloth, with a skirt that moves. Size XL is currently unavailable."),
    dict(name="Black Midi Skirt", brand="Marlowe", category="dresses", price="82.00", material="Wool crepe", popularity=62, kind="dress", bg="#1c1917", ink="#3a3633", colors=[("Black", "#1c1917")], sizes=["XS", "S", "M", "L"], description="A black midi skirt with a clean waistband. Pair it with the ivory camisole or the white shirt."),
    dict(name="Tailored Black Trousers", brand="Atelier North", category="trousers", price="110.00", material="Wool stretch", popularity=92, flags={"is_bestseller": True, "is_featured": True}, kind="trouser", bg="#221f1d", ink="#4a4541", colors=[("Black", "#1c1917")], sizes=["XS", "S", "M", "L", "XL"], description="Black trousers with a straight leg and a pressed crease. They are the bottom half of most outfits in this shop."),
    dict(name="Wide-Leg Cream Trousers", brand="Lumen", category="trousers", price="118.00", material="Viscose twill", popularity=68, flags={"is_new": True, "is_trending": True}, kind="trouser", bg="#f4efe6", ink="#ddd2c2", colors=[("Cream", "#f3ecdf")], sizes=["XS", "S", "M", "L"], description="Cream wide-leg trousers with a high rise. They soften a black knit and a beige blazer."),
    dict(name="Indigo Straight Jeans", brand="Vesper", category="denim", price="88.00", material="Organic denim", popularity=74, flags={"is_trending": True}, kind="denim", bg="#2d3e58", ink="#9aafc4", colors=[("Indigo", "#2d3e58")], sizes=["26", "27", "28", "29", "30", "31", "32"], description="Straight indigo jeans with a mid rise. They take a boot or a clean sneaker."),
    dict(name="Vintage Wash Denim Jacket", brand="Vesper", category="denim", price="120.00", material="Cotton denim", popularity=63, kind="denim", bg="#6d7c8a", ink="#e4e7ea", colors=[("Indigo", "#6d7c8a")], sizes=["XS", "S", "M", "L", "XL"], description="A faded denim jacket with a slightly cropped hem. It is the weekend layer over the striped tee."),
    dict(name="Leather Chelsea Boots", brand="Atelier North", category="shoes", price="180.00", material="Calf leather", popularity=81, flags={"is_featured": True, "is_bestseller": True}, kind="shoe", bg="#6b4b32", ink="#2a1c12", colors=[("Brown", "#6b4b32")], sizes=["36", "37", "38", "39", "40", "41", "42"], description="Brown leather Chelsea boots with a low block heel. They finish trousers and dresses."),
    dict(name="White Leather Sneakers", brand="Halden", category="shoes", price="130.00", material="Leather", popularity=77, flags={"is_new": True, "is_trending": True}, kind="shoe", bg="#f7f7f5", ink="#dedad4", colors=[("White", "#f4f4f2")], sizes=["36", "37", "38", "39", "40", "41", "42"], description="White leather sneakers with a slim sole. The casual alternative to the Chelsea boot."),
    dict(name="Minimal Leather Belt", brand="Sable & Co", category="accessories", price="48.00", material="Leather", popularity=44, kind="accessory", bg="#f6f1ea", ink="#6b4b32", colors=[("Brown", "#6b4b32"), ("Black", "#1c1917")], sizes=["S", "M", "L"], description="A slim leather belt in brown or black. It is there when the trouser needs a line."),
    dict(name="Camel Wool Scarf", brand="Lumen", category="accessories", price="58.00", material="Wool", popularity=52, flags={"is_featured": True}, kind="accessory", bg="#c6a37a", ink="#f6f1ea", colors=[("Camel", "#c6a37a")], sizes=["One"], description="A camel wool scarf, long enough to wrap twice. It warms the charcoal coat."),
    dict(name="Gold Hoop Earrings", brand="Sable & Co", category="accessories", price="36.00", material="Gold-tone metal", popularity=48, flags={"is_new": True}, kind="accessory", bg="#f6f1ea", ink="#c6a15b", colors=[("Gold", "#c6a15b")], sizes=["One"], stock={"One": 3}, threshold=5, description="Small gold hoop earrings. A single finish for the slip dress or the white shirt."),
]


def _role(db, name: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name)
        db.add(role)
        db.flush()
    return role


def _user(db, email: str, password: str, full_name: str, role_name: str) -> User:
    user = db.scalar(select(User).options(selectinload(User.role)).where(User.email == email))
    if user:
        return user
    user = User(email=email, password_hash=hash_password(password), full_name=full_name, role=_role(db, role_name))
    db.add(user)
    db.flush()
    db.add(CustomerProfile(user_id=user.id, phone="555-0100" if role_name == "customer" else None))
    db.add(CustomerStyleProfile(user_id=user.id))
    return user


def _seed_catalog(db) -> None:
    if db.scalar(select(PromoCode).where(PromoCode.code == "WELCOME10")) is None:
        db.add(PromoCode(code="WELCOME10", percent_off=10, min_subtotal=Decimal("0")))
    if db.scalar(select(Product.id).limit(1)):
        return
    categories = {}
    for name, slug, description, order, bg, ink, kind in CATEGORIES:
        image = write_svg(slug, bg, ink, kind, name.upper())
        category = Category(name=name, slug=slug, description=description, image_url=image, sort_order=order)
        db.add(category)
        db.flush()
        categories[slug] = category
    for index, raw in enumerate(PRODUCTS):
        image = write_svg(raw["name"].lower().replace(" ", "-").replace("&", "and"), raw["bg"], raw["ink"], raw["kind"], raw["brand"].upper())
        slug = raw["name"].lower().replace("&", "and")
        slug = "-".join(slug.split())
        flags = raw.get("flags", {})
        product = Product(
            category_id=categories[raw["category"]].id,
            name=raw["name"],
            slug=slug,
            description=raw["description"],
            brand=raw["brand"],
            price=Decimal(raw["price"]),
            compare_at_price=Decimal(raw["compare"]) if raw.get("compare") else None,
            material=raw["material"],
            care="Cool wash or specialist clean, as noted on the cloth.",
            is_featured=bool(flags.get("is_featured")),
            is_new=bool(flags.get("is_new")),
            is_bestseller=bool(flags.get("is_bestseller")),
            is_trending=bool(flags.get("is_trending")),
            popularity=raw["popularity"],
        )
        db.add(product)
        db.flush()
        db.add(ProductImage(product_id=product.id, url=image, alt=raw["name"], sort_order=0, is_primary=True))
        threshold = raw.get("threshold", 5)
        for color, hex_value in raw["colors"]:
            for size in raw["sizes"]:
                sku = f"AT-{index+1:02d}-{color[:3].upper()}-{size}".replace(" ", "")
                variant = ProductVariant(product_id=product.id, sku=sku, size=size, color=color, color_hex=hex_value)
                db.add(variant)
                db.flush()
                quantity = raw.get("stock", {}).get(size, 8)
                db.add(Inventory(variant_id=variant.id, quantity=quantity, low_stock_threshold=threshold))
def _seed_customer_order(db, customer: User) -> None:
    if db.scalar(select(Order.id).where(Order.user_id == customer.id)):
        return
    if not customer.addresses:
        db.add(
            Address(
                user_id=customer.id,
                label="Home",
                full_name=customer.full_name,
                line1="18 Example Lane",
                city="Portland",
                region="OR",
                postal_code="97201",
                country="United States",
                is_default=True,
            )
        )
    style = db.scalar(select(CustomerStyleProfile).where(CustomerStyleProfile.user_id == customer.id))
    if style and not style.favorite_colors:
        style.preferred_sizes = ["M"]
        style.favorite_colors = ["Black", "Cream"]
        style.favorite_categories = ["tops", "trousers"]
        style.preferred_brands = ["Halden", "Atelier North"]
        style.style_keywords = ["minimal", "tailored"]
        style.budget_max = Decimal("200")
    camisole = db.scalar(select(Product).where(Product.slug == "ivory-silk-camisole"))
    trousers = db.scalar(select(Product).where(Product.slug == "tailored-black-trousers"))
    if camisole is None or trousers is None:
        return
    def variant(product, size):
        return db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id, ProductVariant.size == size))
    first = variant(camisole, "M")
    second = variant(trousers, "M")
    order = Order(
        user_id=customer.id,
        number="AT-DEMO1001",
        status="delivered",
        email=customer.email,
        shipping_address={"full_name": customer.full_name, "line1": "18 Example Lane", "city": "Portland", "region": "OR", "postal_code": "97201", "country": "United States"},
        subtotal=Decimal("178.00"),
        shipping_fee=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=Decimal("178.00"),
        currency="USD",
    )
    db.add(order)
    db.flush()
    for product, item, qty in ((camisole, first, 1), (trousers, second, 1)):
        if item is None:
            continue
        db.add(OrderItem(order_id=order.id, variant_id=item.id, product_name=product.name, sku=item.sku, size=item.size, color=item.color, unit_price=product.price, quantity=qty, image_url=product.images[0].url if product.images else None))
    db.add(Payment(order_id=order.id, provider="mock", status="paid", amount=Decimal("178.00")))


def _pages(db, admin: User) -> None:
    from app.models import Page

    if db.scalar(select(Page.id).limit(1)):
        return
    hoodie = db.scalar(select(Product).where(Product.slug == "black-oversized-hoodie"))
    dress = db.scalar(select(Product).where(Product.slug == "midnight-slip-dress"))
    coat = db.scalar(select(Product).where(Product.slug == "charcoal-wool-overcoat"))
    ids = [str(item.id) for item in (hoodie, dress, coat) if item]
    specs = [
        ("About Atelier", "about", "A short introduction to the house.", {"blocks": [
            {"type": "hero", "eyebrow": "The house", "title": "Clothes for a life with somewhere to be", "subtitle": "Atelier is a small line of tailoring, knits, and dresses in a quiet palette.", "cta_label": "Shop the edit", "cta_href": "/shop"},
            {"type": "text", "heading": "How we choose", "body": "We design a short list of pieces that work together. Black, cream, navy, olive, sand, and camel are the colors we return to. Nothing here is a costume."},
        ]}),
        ("Questions", "faq", "Shipping, sizing, and returns.", {"blocks": [
            {"type": "faq", "title": "Before you order", "items": [
                {"question": "How long does shipping take?", "answer": "Standard delivery takes 3 to 5 business days after an order ships. Shipping is $8, and orders of $150 or more ship free."},
                {"question": "What is your return policy?", "answer": "Unworn items with tags can be returned within 30 days of delivery. Refunds go to the original payment method after inspection."},
                {"question": "How do I track an order?", "answer": "Sign in and open your orders. Status moves from paid to processing, shipped, and delivered."},
            ]},
        ]}),
        ("Privacy", "privacy", "What we store, and what we do not.", {"blocks": [
            {"type": "text", "heading": "Privacy", "body": "We store your name, email, optional phone, addresses, orders, wishlist, and any style preferences you choose to save. You can edit, clear, or opt out of style preferences. We never store card numbers. The shopping assistant can read only your own account."},
        ]}),
        ("Terms", "terms", "The terms of shopping at Atelier.", {"blocks": [
            {"type": "text", "heading": "Terms", "body": "Orders are offers to buy the items listed at the price shown at checkout. We may cancel an order if an item is no longer in stock, and we will not charge you for it. Demo accounts in this project are for local testing only."},
        ]}),
        ("Shipping and returns", "shipping-returns", "Fees, timing, and how to send something back.", {"blocks": [
            {"type": "text", "heading": "Shipping", "body": "Shipping is a flat $8 inside the United States. Orders with a merchandise subtotal of $150 or more ship free, before promo codes. Delivery takes 3 to 5 business days after the order ships. We do not currently ship outside the United States."},
            {"type": "text", "heading": "Returns", "body": "Return unworn items with tags within 30 days of delivery. Shipping fees are refunded only when we made an error. Contact the studio with your order number to start a return."},
        ]}),
    ]
    if ids:
        specs.append(("Summer edit", "summer-edit", "A small landing page for warm-weather pieces.", {"blocks": [
            {"type": "hero", "eyebrow": "Summer", "title": "Light cloth, same standards", "subtitle": "Linen, slips, and the pieces that travel.", "image_url": "/static/products/dresses.svg", "cta_label": "Shop dresses", "cta_href": "/shop?category=dresses"},
            {"type": "product_grid", "title": "From the floor", "product_ids": ids},
            {"type": "promo_banner", "title": "Ten percent off your first order", "subtitle": "Use WELCOME10 at checkout.", "cta_label": "Shop", "cta_href": "/shop", "tone": "dark"},
            {"type": "newsletter", "title": "Notes from the studio", "subtitle": "A short letter when new pieces arrive. No noise."},
        ]}))
    for title, slug, summary, definition in specs:
        page = create_page(db, admin, title, definition, slug, summary)
        publish_page(db, admin, page.id, confirm=True)


def seed() -> None:
    db = get_session_factory()()
    try:
        _seed_catalog(db)
        admin = _user(db, "admin@atelier.test", "AtelierAdmin!2026", "Avery Quinn", "admin")
        customer = _user(db, "customer@atelier.test", "AtelierCustomer!2026", "Sloane Mercer", "customer")
        db.commit()
        customer = db.scalar(select(User).options(selectinload(User.addresses), selectinload(User.role)).where(User.email == "customer@atelier.test"))
        _seed_customer_order(db, customer)
        db.commit()
        admin = db.scalar(select(User).options(selectinload(User.role)).where(User.email == "admin@atelier.test"))
        _pages(db, admin)
        ingest_store_documents(db)
        ingest_product_catalog(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed complete.")
