"""
Facebook Routes - Router Principal
Agrega todos los endpoints y exporta router único
"""

from fastapi import APIRouter

# Crear router vacío por defecto
router = APIRouter(prefix="/facebook", tags=["facebook"])

try:
    from .endpoints import (
        scraping_router,
        runs_router,
        storage_router,
        workflows_router,
        analysis_router
    )

    # Incluir todos los routers
    router.include_router(scraping_router)
    router.include_router(runs_router)
    router.include_router(storage_router)
    router.include_router(workflows_router)
    router.include_router(analysis_router)
    
except Exception as e:
    # Si hay error en imports (ej: apify_client no instalado),
    # mantener router vacío
    print(f"WARNING: facebook_routes endpoints no cargados: {e}")
    pass

__all__ = ['router']
