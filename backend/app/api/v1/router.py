# ============================================================
# SalesOS AI — V1 Router Aggregator
# All v1 API routes are registered here.
# ============================================================

from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.health import router as health_router
from app.api.v1.leads import router as leads_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.public import router as public_router
from app.api.v1.sales_execution import router as sales_execution_router

api_v1_router = APIRouter(prefix="/api/v1")

# Register all routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(leads_router)
api_v1_router.include_router(public_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(meetings_router)
api_v1_router.include_router(sales_execution_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(copilot_router)
api_v1_router.include_router(health_router)
