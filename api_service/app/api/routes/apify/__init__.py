"""
Paquete apify - Endpoints para integracion con Apify API
Contiene routers para gestion de actors y extraccion de anuncios por red social
"""
from .apify_routes import router

__all__ = [
    "router",
    "tiktok",
    "facebook",
    "instagram"
]
