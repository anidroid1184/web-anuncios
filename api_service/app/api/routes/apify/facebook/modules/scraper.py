"""
Módulo de Scraping - Endpoints para interactuar con Apify
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, AnyUrl
from typing import Optional
from ..facebook_actor import FacebookActor

router = APIRouter()


class ScrapeRequest(BaseModel):
    """Request model para iniciar un scrape"""
    url: AnyUrl = Field(
        ...,
        description="URL de Facebook Ads Library a scrapear"
    )
    count: int = Field(
        100,
        ge=1,
        le=1000,
        description="Número de anuncios a extraer (1-1000)"
    )


@router.post("/scrape", tags=["scraper"])
async def scrape_facebook_ads(request: ScrapeRequest):
    """
    Inicia un scrape de Facebook Ads Library usando Apify.

    Returns:
        {
            "status": "success",
            "actor_run_id": "...",
            "dataset_id": "...",
            "message": "..."
        }
    """
    try:
        actor = FacebookActor()
        result = await actor.start_scrape(
            url=str(request.url),
            count=request.count
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{actor_run_id}", tags=["scraper"])
async def get_scrape_status(actor_run_id: str):
    """
    Obtiene el estado de un scrape en ejecución.

    Args:
        actor_run_id: ID del run de Apify

    Returns:
        {
            "status": "RUNNING" | "SUCCEEDED" | "FAILED",
            "elapsed_seconds": ...,
            "dataset_id": "..."
        }
    """
    try:
        actor = FacebookActor()
        status = await actor.get_status(actor_run_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/wait/{actor_run_id}", tags=["scraper"])
async def wait_for_scrape(
    actor_run_id: str,
    timeout: int = Query(300, ge=10, le=3600,
                         description="Timeout en segundos")
):
    """
    Espera a que un scrape termine (bloquea hasta completar o timeout).

    Args:
        actor_run_id: ID del run de Apify
        timeout: Tiempo máximo de espera en segundos

    Returns:
        {
            "status": "SUCCEEDED" | "FAILED" | "TIMEOUT",
            "elapsed_seconds": ...,
            "dataset_id": "..."
        }
    """
    try:
        actor = FacebookActor()
        result = await actor.wait_for_completion(
            actor_run_id,
            timeout_seconds=timeout
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
