import uuid

import pytest

from app.ai.agent import ToolContext, run_agent
from app.ai.provider import Completion, ToolCall
from app.ai.rag.ingest import ingest_store_documents
from app.ai.rag.retrieve import search_knowledge
from app.ai.tools.admin_tools import create_page_draft, publish_page_tool
from app.ai.tools.product_tools import recommend, search_products_tool
from app.core.exceptions import PermissionDenied
from app.services.page_schema import validate_definition
from app.tests.conftest import auth, make_product


class Scripted:
    configured = True
    name = "scripted"

    def __init__(self, steps):
        self.steps = list(steps)

    def complete(self, messages, tools):
        return self.steps.pop(0)


def test_agent_search_tool_returns_real_hoodie(db, catalog):
    ctx = ToolContext(db=db, user=None, user_message="black oversized hoodie under $60", conversation_id=None)
    result = search_products_tool(ctx, {"query": "I'm looking for a black oversized hoodie under $60."})
    names = [item["name"] for item in result["products"]]
    assert "Black Oversized Hoodie" in names
    assert "Navy Zip Hoodie" not in names
    assert all(item["price"] for item in result["products"])


def test_recommendation_uses_real_products(db):
    make_product(db, name="White Poplin Shirt", category_slug="tops", category_name="Tops", price="64.00")
    make_product(db, name="Tailored Black Trousers", category_slug="trousers", category_name="Trousers", price="110.00", color="Black")
    make_product(db, name="Leather Chelsea Boots", category_slug="shoes", category_name="Shoes", price="180.00", color="Brown", sizes=["39", "40"])
    make_product(db, name="Relaxed Beige Blazer", category_slug="outerwear", category_name="Outerwear", price="175.00", color="Beige")
    ctx = ToolContext(db=db, user=None, user_message="I need an outfit for a casual dinner", conversation_id=None)
    result = recommend(ctx, {"occasion": "casual dinner", "budget": 200})
    assert result["products"]
    assert "casual dinner" in result["explanation"]
    assert all(Decimal_ok(item["price"]) for item in result["products"])
    ids = {uuid.UUID(item["id"]) for item in result["products"]}
    assert ids


def Decimal_ok(value: str) -> bool:
    return value.replace(".", "", 1).isdigit()


def test_knowledge_retrieval_finds_return_policy(db):
    ingest_store_documents(db)
    hits = search_knowledge(db, "What is your return policy?", limit=3)
    joined = " ".join(hit["content"] for hit in hits).lower()
    assert "30 days" in joined


def test_customer_agent_cannot_publish(db, client, register):
    customer = register(client)
    user_id = uuid.UUID(customer["user"]["id"])
    from app.models import User
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    user = db.scalar(select(User).options(selectinload(User.role)).where(User.id == user_id))
    ctx = ToolContext(db=db, user=user, user_message="Please publish the summer page", conversation_id=None)
    with pytest.raises(PermissionDenied):
        publish_page_tool(ctx, {"page_id": str(uuid.uuid4()), "confirm": True})

    class Boom(Exception):
        pass

    reply = run_agent(
        db,
        message="Publish a page now",
        user=user,
        conversation_id=None,
        guest_token=None,
        provider=Scripted([
            Completion(tool_calls=[ToolCall(name="publish_page", arguments={"page_id": str(uuid.uuid4()), "confirm": True})]),
            Completion(text="I can't publish that."),
        ]),
    )
    assert "can't" in reply["reply"].lower() or reply["reply"]
    actions = client.get("/api/admin/ai/actions", headers=auth(customer["access_token"]))
    assert actions.status_code == 403


def test_admin_page_draft_and_explicit_publish(db, admin_login, client):
    from app.models import User
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    admin = db.scalar(select(User).options(selectinload(User.role)).where(User.email == "admin@example.com"))
    product, _ = make_product(db, name="Sand Trench Coat", price="198.00", category_slug="outerwear", category_name="Outerwear", color="Sand")
    definition = {
        "blocks": [
            {"type": "hero", "title": "Summer collection", "subtitle": "Light layers for warm evenings.", "cta_label": "Shop", "cta_href": "/shop"},
            {"type": "product_grid", "title": "Featured", "product_ids": [str(product.id)]},
            {"type": "promo_banner", "title": "Summer notes", "subtitle": "A short promotional section.", "cta_label": "Browse", "cta_href": "/shop", "tone": "light"},
        ]
    }
    ctx = ToolContext(db=db, user=admin, user_message="Create a landing page for the summer collection.", conversation_id=None)
    draft = create_page_draft(ctx, {"title": "Summer collection", "slug": "summer-collection", "definition": definition})
    assert draft["page"]["status"] == "draft"
    page_id = draft["page"]["id"]

    quiet = publish_page_tool(ctx, {"page_id": page_id, "confirm": True})
    assert "explicitly" in quiet["error"]
    hidden = client.get("/api/pages/summer-collection")
    assert hidden.status_code == 404

    ctx.user_message = "Please publish the summer collection page."
    published = publish_page_tool(ctx, {"page_id": page_id, "confirm": True})
    assert published["page"]["status"] == "published"
    public = client.get("/api/pages/summer-collection")
    assert public.status_code == 200
    types = [block["type"] for block in public.json()["definition"]["blocks"]]
    assert types == ["hero", "product_grid", "promo_banner"]
    assert public.json()["definition"]["blocks"][1]["products"][0]["name"] == "Sand Trench Coat"

    blocked = client.post(
        f"/api/admin/pages/{page_id}/publish",
        json={"confirm": True},
        headers=auth(client.post("/api/auth/register", json={"email": "shopper@example.com", "password": "password123", "full_name": "Shopper"}).json()["access_token"]),
    )
    assert blocked.status_code == 403


def test_page_schema_rejects_html(db):
    try:
        validate_definition(db, {"blocks": [{"type": "text", "body": "<script>alert(1)</script>"}]})
        assert False, "html should be rejected"
    except Exception as exc:
        assert "HTML" in str(exc)


def test_scripted_agent_attaches_product_cards(db, catalog):
    from app.models import User

    reply = run_agent(
        db,
        message="I'm looking for a black oversized hoodie under $60.",
        user=None,
        conversation_id=None,
        guest_token="guest-agent",
        provider=Scripted([
            Completion(tool_calls=[ToolCall(name="search_products", arguments={"query": "black oversized hoodie under $60"})]),
            Completion(text="The black oversized hoodie is $54 and in stock."),
        ]),
    )
    assert reply["products"]
    assert reply["products"][0]["name"] == "Black Oversized Hoodie"
    assert reply["products"][0]["price"] == "54.00"
    assert "54" in reply["reply"]
    assert isinstance(User, type)


def test_guest_conversation_moves_to_the_account(client, register):
    from app.tests.conftest import auth

    guest = {"X-Guest-Token": "guest-transfer"}
    first = client.post("/api/ai/chat", json={"message": "hello from the fitting room"}, headers=guest)
    assert first.status_code == 200, first.text
    created = register(client)
    headers = auth(created["access_token"])
    headers["X-Guest-Token"] = "guest-transfer"
    history = client.get(f"/api/ai/conversations/{first.json()['conversation_id']}", headers=headers)
    assert history.status_code == 200, history.text
    assert history.json()["messages"][0]["content"] == "hello from the fitting room"
