"""
Paquete Facebook - Scraper de anuncios de Facebook usando Apify
Usa el paquete refactorizado facebook_routes con arquitectura modular
"""
from fastapi import APIRouter

# Importar el router del paquete refactorizado
try:
    from .facebook_routes import router as facebook_routes_router
    
    # Usar el router refactorizado
    router = facebook_routes_router
    
except ImportError as e:
    # Fallback a estructura antigua si facebook_routes no está disponible
    print(f"WARNING: No se pudo importar facebook_routes: {e}")
    print("Usando estructura de routes antigua...")
    
    try:
        from .routes.scraper import router as scraper_router
        from .routes.runs import router as runs_router
        from .routes.management import router as management_router
        from .routes.analysis import router as analysis_router
        
        # Create main router
        router = APIRouter(tags=["Facebook"])
        
        # Include sub-routers
        router.include_router(scraper_router)
        router.include_router(runs_router)
        router.include_router(management_router)
        router.include_router(analysis_router)
        
    except ImportError:
        # Crear router vacío si nada funciona
        router = APIRouter(tags=["Facebook"])
        print("ERROR: No se pudieron cargar los routers de Facebook")

__all__ = ["router"]
