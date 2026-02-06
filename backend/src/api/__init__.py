"""
API routers for AI Tax Assistant.
"""

from fastapi import APIRouter

from src.api.delivery import router as delivery_router
from src.api.documents import router as documents_router
from src.api.enrichment import router as enrichment_router
from src.api.transactions import router as transactions_router

# Main API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(transactions_router)
api_router.include_router(enrichment_router)
api_router.include_router(documents_router)
api_router.include_router(delivery_router)

__all__ = ["api_router"]
