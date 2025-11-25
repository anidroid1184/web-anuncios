"""
Facebook Routes - Endpoints de Storage (GCS)
Operaciones con Google Cloud Storage
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from ..services import StorageService
from ..config import path_resolver
import os

router = APIRouter(prefix="/storage", tags=["storage"])

# Inicializar servicio (GCS opcional)
try:
    from app.services.gcs_service import GCSService
    gcs_service = GCSService()
    storage_service = StorageService(gcs_service)
except ImportError:
    storage_service = StorageService(None)


@router.post("/{run_id}/upload")
async def upload_to_gcs(
    run_id: str,
    bucket_name: str,
    prefix: Optional[str] = None
):
    """
    Sube un run completo a GCS.

    Args:
        run_id: ID del run
        bucket_name: Nombre del bucket
        prefix: Prefijo opcional en GCS

    Returns:
        Resultado del upload
    """
    try:
        base_path = path_resolver.get_facebook_saved_base()
        run_path = base_path / run_id

        if not run_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Run {run_id} no encontrado"
            )

        result = await storage_service.upload_dataset(
            run_id,
            run_path,
            bucket_name,
            prefix
        )

        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}/urls")
async def get_public_urls(
    run_id: str,
    bucket_name: str,
    prefix: Optional[str] = None
):
    """
    Obtiene URLs públicas de archivos en GCS.

    Args:
        run_id: ID del run
        bucket_name: Nombre del bucket
        prefix: Prefijo para filtrar

    Returns:
        Lista de URLs públicas
    """
    try:
        result = await storage_service.get_public_urls(
            run_id,
            bucket_name,
            prefix
        )

        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}/files")
async def list_gcs_files(run_id: str, bucket_name: str):
    """
    Lista archivos de un run en GCS.

    Args:
        run_id: ID del run
        bucket_name: Nombre del bucket

    Returns:
        Lista de archivos con metadata
    """
    try:
        files = await storage_service.list_run_files(run_id, bucket_name)
        return {
            "success": True,
            "run_id": run_id,
            "bucket": bucket_name,
            "count": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{run_id}/manifest")
async def save_manifest(
    run_id: str,
    bucket_name: str,
    manifest_data: dict
):
    """
    Guarda un manifest para un run.

    Args:
        run_id: ID del run
        bucket_name: Bucket de destino
        manifest_data: Datos del manifest

    Returns:
        Resultado de la operación
    """
    try:
        base_path = path_resolver.get_facebook_saved_base()
        local_path = base_path / run_id

        result = await storage_service.save_manifest(
            run_id,
            manifest_data,
            bucket_name,
            local_path if local_path.exists() else None
        )

        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
