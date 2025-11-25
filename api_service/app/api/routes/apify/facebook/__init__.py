"""
Paquete Facebook - Scraper de anuncios de Facebook usando Apify
Usa el paquete refactorizado facebook_routes con arquitectura modular
"""
from fastapi import APIRouter
import logging
import traceback

logger = logging.getLogger("ads_analyzer.facebook_init")

# PRIORIZAR estructura modular de routes/ sobre facebook_routes.py monolítico
try:
    from .routes.scraper import router as scraper_router
    from .routes.runs import router as runs_router
    from .routes.management import router as management_router
    from .routes.analysis import router as analysis_router
    from .modules.campaign_analysis import router as campaign_analysis_router
    from .modules.local_analysis import router as local_analysis_router

    # Create main router
    router = APIRouter(tags=["Facebook"])

    # Include sub-routers (ya tienen tag Facebook individual)
    router.include_router(scraper_router)
    router.include_router(runs_router)
    router.include_router(management_router)
    router.include_router(analysis_router)
    router.include_router(campaign_analysis_router)
    router.include_router(local_analysis_router)

    logger.info("✓ Facebook routes cargadas desde estructura modular")

except ImportError as e:
    # Fallback a facebook_routes.py monolítico
    logger.warning("No se pudo cargar estructura modular: %s", e)
    logger.debug(traceback.format_exc())
    logger.info("Intentando facebook_routes.py monolítico...")

    try:
        from .facebook_routes import router as facebook_routes_router
        router = facebook_routes_router
        logger.info("✓ Facebook routes cargadas desde facebook_routes.py")
    except ImportError:
        # Crear router vacío si nada funciona
        router = APIRouter(tags=["Facebook"])
        logger.error("✗ No se pudieron cargar los routers de Facebook")

__all__ = ["router"]
