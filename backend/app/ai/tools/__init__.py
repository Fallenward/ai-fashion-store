from app.ai.tools.admin_tools import (
    create_page_draft,
    get_page_preview,
    publish_page_tool,
    unpublish_page_tool,
    update_page_draft,
)
from app.ai.tools.customer_tools import (
    get_customer_order_history,
    get_customer_style_profile,
    get_customer_wishlist,
    update_customer_style_profile,
)
from app.ai.tools.knowledge_tools import ingest_catalog, ingest_documents, rebuild_index, retrieve_product_information, search_store_knowledge
from app.ai.tools.product_tools import (
    compare_products,
    get_product_details,
    get_product_inventory,
    get_related_products,
    recommend,
    search_products_tool,
)

OBJECT = "object"
STRING = "string"
ARRAY = "array"
NUMBER = "number"
BOOLEAN = "boolean"


def _params(properties: dict, required: list[str] | None = None) -> dict:
    schema = {"type": OBJECT, "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _str(description: str) -> dict:
    return {"type": STRING, "description": description}


def _num(description: str) -> dict:
    return {"type": NUMBER, "description": description}


TOOLS = [
    {
        "name": "search_products",
        "description": "Search the live catalog by words, category, size, color, brand, and price. Use this before naming products.",
        "admin_only": False,
        "handler": search_products_tool,
        "parameters": _params(
            {
                "query": _str("Natural language such as oversized hoodie."),
                "category": _str("Category slug such as tops, dresses, outerwear, knitwear, trousers, denim, shoes, accessories."),
                "size": _str("Size such as S, M, L, XL."),
                "color": _str("Color name such as black."),
                "brand": _str("Brand name."),
                "min_price": _num("Minimum price in USD."),
                "max_price": _num("Maximum price in USD."),
                "in_stock": {"type": BOOLEAN, "description": "Defaults to in-stock only."},
                "limit": _num("Maximum products, up to 8."),
            }
        ),
    },
    {
        "name": "get_product_details",
        "description": "Get the live description, price, sizes, colors, and stock for one product.",
        "admin_only": False,
        "handler": get_product_details,
        "parameters": _params({"product_id": _str("Product id."), "slug": _str("Product slug.")}),
    },
    {
        "name": "get_product_inventory",
        "description": "Check live quantity for each size and color of a product.",
        "admin_only": False,
        "handler": get_product_inventory,
        "parameters": _params({"product_id": _str("Product id.")}, ["product_id"]),
    },
    {
        "name": "compare_products",
        "description": "Compare up to four real products, including price, material, and stock.",
        "admin_only": False,
        "handler": compare_products,
        "parameters": _params({"product_ids": {"type": ARRAY, "items": {"type": STRING}, "description": "Product ids."}}, ["product_ids"]),
    },
    {
        "name": "get_related_products",
        "description": "Find in-stock products in the same category.",
        "admin_only": False,
        "handler": get_related_products,
        "parameters": _params({"product_id": _str("Product id.")}, ["product_id"]),
    },
    {
        "name": "recommend_products",
        "description": "Build an outfit or a short list from real in-stock products, a budget, an occasion, and saved preferences.",
        "admin_only": False,
        "handler": recommend,
        "parameters": _params(
            {
                "occasion": _str("Examples: casual dinner, office, weekend, summer."),
                "budget": _num("Maximum spend for the pieces, in USD."),
                "colors": {"type": ARRAY, "items": {"type": STRING}},
                "categories": {"type": ARRAY, "items": {"type": STRING}},
                "brands": {"type": ARRAY, "items": {"type": STRING}},
                "sizes": {"type": ARRAY, "items": {"type": STRING}},
                "limit": _num("How many pieces, up to 6."),
            }
        ),
    },
    {
        "name": "get_customer_style_profile",
        "description": "Read the signed-in customer's saved style preferences. Returns opted_out when they have turned personalization off.",
        "admin_only": False,
        "handler": get_customer_style_profile,
        "parameters": _params({"customer_id": _str("Only an administrator may pass another customer id.")}),
    },
    {
        "name": "update_customer_style_profile",
        "description": "Save style preferences the customer just agreed to. Pass opt_out true to stop using saved preferences.",
        "admin_only": False,
        "handler": update_customer_style_profile,
        "parameters": _params(
            {
                "preferred_sizes": {"type": ARRAY, "items": {"type": STRING}},
                "favorite_colors": {"type": ARRAY, "items": {"type": STRING}},
                "favorite_categories": {"type": ARRAY, "items": {"type": STRING}},
                "preferred_brands": {"type": ARRAY, "items": {"type": STRING}},
                "style_keywords": {"type": ARRAY, "items": {"type": STRING}},
                "budget_min": _num("Minimum budget."),
                "budget_max": _num("Maximum budget."),
                "notes": _str("Short note the customer agreed to save."),
                "opt_out": {"type": BOOLEAN, "description": "True clears and disables saved preferences."},
            }
        ),
    },
    {
        "name": "get_customer_wishlist",
        "description": "Read the signed-in customer's wishlist.",
        "admin_only": False,
        "handler": get_customer_wishlist,
        "parameters": _params({}),
    },
    {
        "name": "get_customer_order_history",
        "description": "Read the signed-in customer's recent orders and statuses for tracking questions.",
        "admin_only": False,
        "handler": get_customer_order_history,
        "parameters": _params({}),
    },
    {
        "name": "search_store_knowledge",
        "description": "Search shipping, returns, FAQ, privacy, and brand notes. Do not use this for live price or stock.",
        "admin_only": False,
        "handler": search_store_knowledge,
        "parameters": _params({"query": _str("The customer's question.")}, ["query"]),
    },
    {
        "name": "retrieve_product_information",
        "description": "Find product references by meaning, then hydrate live cards. Still confirm stock with this result's products, which are live.",
        "admin_only": False,
        "handler": retrieve_product_information,
        "parameters": _params({"query": _str("What the customer described.")}, ["query"]),
    },
    {
        "name": "ingest_product_catalog",
        "description": "Admin only. Rebuild product documents in the knowledge index.",
        "admin_only": True,
        "handler": ingest_catalog,
        "parameters": _params({}),
    },
    {
        "name": "ingest_store_documents",
        "description": "Admin only. Rebuild policy and FAQ documents in the knowledge index.",
        "admin_only": True,
        "handler": ingest_documents,
        "parameters": _params({}),
    },
    {
        "name": "rebuild_vector_index",
        "description": "Admin only. Recompute embeddings for the knowledge index.",
        "admin_only": True,
        "handler": rebuild_index,
        "parameters": _params({}),
    },
    {
        "name": "create_page_draft",
        "description": "Admin only. Save a validated JSON page as a draft. Never publish from this tool.",
        "admin_only": True,
        "handler": create_page_draft,
        "parameters": _params(
            {
                "title": _str("Page title."),
                "slug": _str("Optional url slug."),
                "summary": _str("Short summary."),
                "definition": {"type": OBJECT, "description": "Object with a blocks array. Block types: hero, text, image, product_grid, featured_collection, promo_banner, testimonials, faq, newsletter."},
            },
            ["title", "definition"],
        ),
    },
    {
        "name": "update_page_draft",
        "description": "Admin only. Replace the draft definition of an existing page without publishing it.",
        "admin_only": True,
        "handler": update_page_draft,
        "parameters": _params(
            {
                "page_id": _str("Page id."),
                "title": _str("Optional title."),
                "definition": {"type": OBJECT, "description": "Replacement page definition."},
            },
            ["page_id", "definition"],
        ),
    },
    {
        "name": "get_page_preview",
        "description": "Admin only. Read a page draft with live product data resolved.",
        "admin_only": True,
        "handler": get_page_preview,
        "parameters": _params({"page_id": _str("Page id.")}, ["page_id"]),
    },
    {
        "name": "publish_page",
        "description": "Admin only. Publish a draft when the administrator explicitly asked to publish and confirm is true.",
        "admin_only": True,
        "handler": publish_page_tool,
        "parameters": _params({"page_id": _str("Page id."), "confirm": {"type": BOOLEAN, "description": "Must be true."}}, ["page_id", "confirm"]),
    },
    {
        "name": "unpublish_page",
        "description": "Admin only. Take a public page back to draft.",
        "admin_only": True,
        "handler": unpublish_page_tool,
        "parameters": _params({"page_id": _str("Page id.")}, ["page_id"]),
    },
]

TOOL_MAP = {tool["name"]: tool for tool in TOOLS}
PRODUCT_TOOL_NAMES = {
    "search_products",
    "get_product_details",
    "get_product_inventory",
    "compare_products",
    "get_related_products",
    "recommend_products",
    "retrieve_product_information",
    "get_customer_wishlist",
}


def schemas_for(is_admin: bool) -> list[dict]:
    visible = []
    for tool in TOOLS:
        if tool["admin_only"] and not is_admin:
            continue
        visible.append({"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]})
    return visible
