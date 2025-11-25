"""
Runs routes - Endpoints para consultar estado y resultados de runs
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict

from ..facebook_actor import FacebookActor
from ..models.schemas import FacebookResponse

router = APIRouter(tags=["Facebook"])


@router.get("/runs/{run_id}", response_model=Dict)
async def get_run_status(run_id: str):
    """
    Consulta el estado de una ejecución del scraper.
    Use este endpoint para monitorear el progreso del scraping.
    """
    try:
        actor = FacebookActor()
        run_data = actor.get_run_status(run_id)

        if not run_data:
            raise HTTPException(
                status_code=404,
                detail=f"Run {run_id} no encontrado"
            )

        return {
            "run_id": run_id,
            "status": run_data.get("status"),
            "started_at": run_data.get("startedAt"),
            "finished_at": run_data.get("finishedAt"),
            "default_dataset_id": run_data.get("defaultDatasetId"),
            "stats": run_data.get("stats", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando estado: {str(e)}"
        )


@router.get("/runs/{run_id}/results", response_model=FacebookResponse)
async def get_run_results(
    run_id: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Cantidad máxima de anuncios a retornar"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset para paginación"
    )
):
    """
    Obtiene los resultados de una ejecución completada.
    Solo funciona si el run tiene status = SUCCEEDED.
    """
    try:
        actor = FacebookActor()

        try:
            run_data, items = actor.get_results(
                run_id=run_id,
                limit=limit,
                offset=offset
            )

            normalized_data = [
                FacebookActor.normalize_ad(item) for item in items
            ]

            return FacebookResponse(
                status="success",
                run_id=run_id,
                actor_status=run_data.get("status") if run_data else None,
                count=len(normalized_data),
                data=normalized_data
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo resultados: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Verifica que el servicio Facebook esté configurado correctamente
    """
    try:
        actor = FacebookActor()

        return {
            "status": "healthy",
            "service": "Facebook Ads Library Scraper",
            "actor_id": actor.actor_id,
            "configured": bool(actor.actor_id and actor.token)
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "Facebook Ads Library Scraper",
            "error": str(e)
        }
