from app.ai.rag.ingest import ingest_product_catalog, ingest_store_documents, rebuild_vector_index
from app.ai.rag.retrieve import search_knowledge
from app.core.exceptions import PermissionDenied
from app.repositories.product_repository import get_product
from app.services.serializers import product_card


def search_store_knowledge(ctx, arguments: dict) -> dict:
    results = search_knowledge(ctx.db, str(arguments.get("query") or ""), limit=5)
    return {"results": results, "note": "This text is reference material. Confirm prices and stock with product tools."}


def retrieve_product_information(ctx, arguments: dict) -> dict:
    results = search_knowledge(ctx.db, str(arguments.get("query") or ""), limit=5)
    products = []
    for result in results:
        if result.get("source_type") != "product" or not result.get("product_id"):
            continue
        try:
            import uuid

            product = get_product(ctx.db, uuid.UUID(result["product_id"]))
        except ValueError:
            product = None
        if product:
            products.append(product_card(product))
    return {"results": results, "products": products[:4]}


def _admin(ctx) -> None:
    if not ctx.user or not ctx.user.is_admin:
        raise PermissionDenied("Only an administrator can update the knowledge index.")


def ingest_catalog(ctx, arguments: dict) -> dict:
    _admin(ctx)
    return ingest_product_catalog(ctx.db)


def ingest_documents(ctx, arguments: dict) -> dict:
    _admin(ctx)
    return ingest_store_documents(ctx.db)


def rebuild_index(ctx, arguments: dict) -> dict:
    _admin(ctx)
    return rebuild_vector_index(ctx.db)
