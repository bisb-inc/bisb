from fastapi import APIRouter

from app.api.routes.analyses import router as analyses_router
from app.api.routes.event_analyses import router as event_analyses_router
from app.api.routes.health import router as health_router

router = APIRouter()
router.include_router(health_router)
router.include_router(analyses_router)
router.include_router(event_analyses_router)
