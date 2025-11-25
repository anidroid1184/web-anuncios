"""
Facebook Routes - Endpoints de Runs
Gestión de runs guardados localmente
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from ..services import RunsService
from ..config import path_resolver

router = APIRouter(prefix="/runs", tags=["runs"])

# Servicio de runs
runs_service = RunsService(path_resolver.get_facebook_saved_base())


@router.get("/list")
async def list_runs():
    """
    Lista todos los runs guardados.

    Returns:
        Lista de runs con metadata
    """
    try:
        runs = runs_service.list_saved_runs()
        return {
            "success": True,
            "count": len(runs),
            "runs": runs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{run_id}")
async def delete_run(run_id: str):
    """
    Elimina un run específico.

    Args:
        run_id: ID del run a eliminar

    Returns:
        Resultado de la operación
    """
    try:
        result = runs_service.delete_run(run_id)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result['message'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_runs(
    keep_count: int = 10,
    min_size_mb: Optional[float] = None
):
    """
    Limpia runs antiguos.

    Args:
        keep_count: Número de runs a mantener
        min_size_mb: Tamaño mínimo para considerar

    Returns:
        Estadísticas de limpieza
    """
    try:
        result = runs_service.cleanup_old_runs(keep_count, min_size_mb)
        return {
            "success": True,
            "stats": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}/info")
async def get_run_info(run_id: str):
    """
    Obtiene información detallada de un run.

    Args:
        run_id: ID del run

    Returns:
        Metadata del run
    """
    try:
        run_path = path_resolver.get_facebook_saved_base() / run_id
        if not run_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Run {run_id} no encontrado"
            )

        run_info = runs_service._get_run_info(run_path)
        return run_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
