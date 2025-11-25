"""
Facebook Routes - Endpoints Package
Exporta todos los routers de endpoints
"""

from .scraping import router as scraping_router
from .runs import router as runs_router
from .storage import router as storage_router
from .workflows import router as workflows_router
from .analysis import router as analysis_router

__all__ = [
    'scraping_router',
    'runs_router',
    'storage_router',
    'workflows_router',
    'analysis_router'
]
