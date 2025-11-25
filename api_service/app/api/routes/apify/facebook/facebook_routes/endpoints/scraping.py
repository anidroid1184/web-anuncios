"""
Facebook Routes - Endpoints de Scraping
Rutas HTTP para operaciones de scraping
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import sys
from pathlib import Path

# Importar FacebookActor desde dos niveles arriba
current_dir = Path(__file__).resolve().parent
facebook_dir = current_dir.parent.parent
sys.path.insert(0, str(facebook_dir))

from facebook_actor import FacebookActor

from ..models import (
    SimpleScrapeRequest,
    FacebookScraperInput,
    FacebookStartResponse
)
from ..services import ScrapingService

router = APIRouter(prefix="/scrape", tags=["scraping"])

# Dependencia: FacebookActor
facebook_actor = FacebookActor()
scraping_service = ScrapingService(facebook_actor)


@router.post("/simple", response_model=FacebookStartResponse)
async def scrape_simple(request: SimpleScrapeRequest):
    """
    Inicia scraping con configuración simplificada.

    Args:
        request: Parámetros de scraping básicos

    Returns:
        Información del run iniciado
    """
    try:
        result = await scraping_service.scrape_and_save(
            page_url=request.page_url,
            count=request.count,
            country_code=request.country_code,
            platform=request.platform,
            max_concurrency=request.max_concurrency
        )

        return FacebookStartResponse(
            run_id=result['run_id'],
            status=result['status'],
            message=result['message']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/advanced", response_model=FacebookStartResponse)
async def scrape_advanced(request: FacebookScraperInput):
    """
    Inicia scraping con configuración avanzada.

    Args:
        request: Input completo del scraper

    Returns:
        Información del run iniciado
    """
    try:
        input_dict = request.dict(exclude_none=True)
        result = await scraping_service.scrape_with_full_input(input_dict)

        return FacebookStartResponse(
            run_id=result['run_id'],
            status=result['status'],
            message=result['message']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{run_id}")
async def get_status(run_id: str):
    """
    Obtiene el estado de un run.

    Args:
        run_id: ID del run a consultar

    Returns:
        Estado actual del run
    """
    try:
        result = await scraping_service.get_run_status(run_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{run_id}")
async def get_results(run_id: str, limit: Optional[int] = None):
    """
    Obtiene los resultados de un run completado.

    Args:
        run_id: ID del run
        limit: Límite opcional de resultados

    Returns:
        Resultados del scraping
    """
    try:
        result = await scraping_service.get_run_results(run_id, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wait/{run_id}")
async def wait_completion(
    run_id: str,
    timeout: int = 600,
    poll_interval: int = 5
):
    """
    Espera a que un run se complete.

    Args:
        run_id: ID del run
        timeout: Timeout en segundos
        poll_interval: Intervalo de polling

    Returns:
        Estado final del run
    """
    try:
        result = await scraping_service.wait_for_completion(
            run_id,
            timeout,
            poll_interval
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
