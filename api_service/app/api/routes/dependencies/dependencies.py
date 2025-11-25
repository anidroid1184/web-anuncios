"""
Dependencias comunes para los endpoints de la API
"""
from fastapi import HTTPException
from app.services.apify_service import ApifyService
import os


def get_apify_token() -> str:
    """Obtiene el token de Apify de las variables de entorno"""
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise HTTPException(
            status_code=500,
            detail="APIFY_TOKEN environment variable is not configured"
        )
    return token


def get_apify_service() -> ApifyService:
    """Obtiene una instancia de ApifyService con el token configurado"""
    token = get_apify_token()
    return ApifyService(token)


def get_actor_id(env_var_name: str) -> str:
    """Obtiene el ID de un actor desde variables de entorno"""
    actor_id = os.getenv(env_var_name)
    if not actor_id:
        raise HTTPException(
            status_code=500,
            detail=f"{env_var_name} environment variable is not configured"
        )
    return actor_id
