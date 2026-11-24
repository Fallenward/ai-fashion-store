from fastapi import APIRouter

from app.api import account, admin, ai, auth, catalog, commerce, content, payments

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(commerce.router)
api_router.include_router(account.router)
api_router.include_router(content.router)
api_router.include_router(ai.router)
api_router.include_router(admin.router)
api_router.include_router(payments.router)
