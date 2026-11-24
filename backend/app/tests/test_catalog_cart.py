from decimal import Decimal

from app.tests.conftest import auth, make_product


def test_search_black_hoodie_under_60(client, catalog):
    response = client.get("/api/products", params={"q": "black oversized hoodie under $60"})
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert names == ["Black Oversized Hoodie"]
    assert response.json()["items"][0]["price"] == "54.00"


def test_filter_color_size_and_price(client, db):
    make_product(db, name="White Poplin Shirt", price="64.00", color="White", sizes=["S", "M"])
    make_product(db, name="Olive Field Jacket", price="160.00", category_slug="outerwear", category_name="Outerwear", color="Olive", sizes=["M", "L"])
    white = client.get("/api/products", params={"color": "White", "size": "S"})
    assert [item["name"] for item in white.json()["items"]] == ["White Poplin Shirt"]
    cheap = client.get("/api/products", params={"max_price": "70"})
    assert [item["name"] for item in cheap.json()["items"]] == ["White Poplin Shirt"]
    outer = client.get("/api/products", params={"category": "outerwear", "sort": "price_asc"})
    assert outer.json()["items"][0]["name"] == "Olive Field Jacket"


def test_cart_add_update_and_stock_limit(client, catalog):
    variant = str(catalog["hoodie_variants"]["M"])
    headers = {"X-Cart-Token": "guest-cart-1"}
    added = client.post("/api/cart/items", json={"variant_id": variant, "quantity": 2}, headers=headers)
    assert added.status_code == 200, added.text
    assert added.json()["item_count"] == 2
    item_id = added.json()["items"][0]["id"]
    updated = client.patch(f"/api/cart/items/{item_id}", json={"quantity": 1}, headers=headers)
    assert updated.json()["item_count"] == 1
    too_many = client.patch(f"/api/cart/items/{item_id}", json={"quantity": 9}, headers=headers)
    assert too_many.status_code == 400
    removed = client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert removed.json()["items"] == []


def test_checkout_quote_mock_payment_and_stock(client, register, catalog, db):
    from sqlalchemy import select

    from app.models import Inventory

    created = register(client)
    headers = auth(created["access_token"])
    variant = str(catalog["hoodie_variants"]["M"])
    client.post("/api/cart/items", json={"variant_id": variant, "quantity": 2}, headers=headers)
    empty = client.post("/api/checkout/quote", json={}, headers=auth(register(client, email="empty@example.com")["access_token"]))
    assert empty.status_code == 400

    quote = client.post("/api/checkout/quote", json={"promo_code": "WELCOME10"}, headers=headers)
    assert quote.status_code == 200, quote.text
    body = quote.json()
    assert body["payment_mode"] == "mock"
    assert body["subtotal"] == "108.00"
    assert body["discount"] == "10.80"
    assert Decimal(body["total"]) == Decimal("108.00") - Decimal("10.80") + Decimal(body["shipping_fee"])

    order = client.post(
        "/api/checkout",
        json={
            "full_name": "Ada Lovelace",
            "line1": "18 Example Lane",
            "city": "Portland",
            "region": "OR",
            "postal_code": "97201",
            "country": "United States",
            "promo_code": "WELCOME10",
        },
        headers=headers,
    )
    assert order.status_code == 200, order.text
    assert order.json()["mode"] == "mock"
    paid = client.post(f"/api/checkout/{order.json()['order_id']}/mock-pay", headers=headers)
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["payment"]["provider"] == "mock"
    again = client.post(f"/api/checkout/{order.json()['order_id']}/mock-pay", headers=headers)
    assert again.status_code == 400
    inventory = db.scalar(select(Inventory).where(Inventory.variant_id == catalog["hoodie_variants"]["M"]))
    db.refresh(inventory)
    assert inventory.quantity == 6
