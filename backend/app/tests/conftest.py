import os
from decimal import Decimal

os.environ["DATABASE_URL"] = "postgresql+psycopg://fashion:fashion@127.0.0.1:5432/fashion_test"
os.environ["JWT_SECRET"] = "test-secret-key-please-change"
os.environ["APP_ENV"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["LLM_PROVIDER"] = "none"
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["STRIPE_SECRET_KEY"] = ""
os.environ["STRIPE_WEBHOOK_SECRET"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.database import get_engine, get_session_factory, reset_engine
from app.core.security import hash_password
from app.models import Base, Category, CustomerProfile, CustomerStyleProfile, Inventory, Product, ProductImage, ProductVariant, PromoCode, Role, User

get_settings.cache_clear()
reset_engine()


@pytest.fixture(scope="session", autouse=True)
def _schema():
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def _clean():
    engine = get_engine()
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    yield


@pytest.fixture
def db():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def register():
    def _register(client, email="ada@example.com", password="password123", name="Ada Lovelace"):
        response = client.post("/api/auth/register", json={"email": email, "password": password, "full_name": name})
        assert response.status_code == 201, response.text
        return response.json()

    return _register


@pytest.fixture
def admin_login(db, client):
    role = Role(name="admin")
    db.add(role)
    db.flush()
    user = User(email="admin@example.com", password_hash=hash_password("password123"), full_name="Admin User", role=role)
    db.add(user)
    db.flush()
    db.add(CustomerProfile(user_id=user.id))
    db.add(CustomerStyleProfile(user_id=user.id))
    db.commit()
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "password123"})
    assert response.status_code == 200, response.text
    return response.json()


def make_product(
    db,
    *,
    name="Black Oversized Hoodie",
    price="54.00",
    category_slug="tops",
    category_name="Tops",
    color="Black",
    sizes=None,
    stock=8,
    brand="Halden",
    description="A heavy black oversized hoodie.",
):
    category = db.scalar(select(Category).where(Category.slug == category_slug))
    if category is None:
        category = Category(name=category_name, slug=category_slug, description=category_name)
        db.add(category)
        db.flush()
    slug = "-".join(name.lower().split())
    product = Product(
        category_id=category.id,
        name=name,
        slug=slug,
        description=description,
        brand=brand,
        price=Decimal(price),
        material="Cotton",
        popularity=10,
        is_active=True,
    )
    db.add(product)
    db.flush()
    db.add(ProductImage(product_id=product.id, url=f"/static/products/{slug}.svg", alt=name, is_primary=True))
    variant_ids = {}
    for size in sizes or ["S", "M", "L"]:
        variant = ProductVariant(product_id=product.id, sku=f"{slug}-{color}-{size}".upper()[:60], size=size, color=color, color_hex="#111111")
        db.add(variant)
        db.flush()
        db.add(Inventory(variant_id=variant.id, quantity=stock, low_stock_threshold=5))
        variant_ids[size] = variant.id
    db.commit()
    return product, variant_ids


@pytest.fixture
def catalog(db):
    promo = PromoCode(code="WELCOME10", percent_off=10, min_subtotal=Decimal("0"))
    db.add(promo)
    hoodie, hoodie_variants = make_product(db)
    navy, _ = make_product(
        db,
        name="Navy Zip Hoodie",
        price="78.00",
        color="Navy",
        description="A navy zip hoodie above sixty dollars.",
    )
    db.commit()
    return {"hoodie": hoodie, "hoodie_variants": hoodie_variants, "navy": navy}
