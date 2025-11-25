"""
Facebook Routes - Endpoints de Workflows
Workflows complejos que combinan múltiples operaciones
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import sys
from pathlib import Path

# Importar FacebookActor desde dos niveles arriba
current_dir = Path(__file__).resolve().parent
facebook_dir = current_dir.parent.parent
sys.path.insert(0, str(facebook_dir))

from facebook_actor import FacebookActor

from ..models import WorkflowRequest
from ..services import (
    ScrapingService,
    PreparationService,
    UploadService
)
from ..config import path_resolver

router = APIRouter(prefix="/workflows", tags=["workflows"])

# Inicializar servicios
facebook_actor = FacebookActor()
scraping_service = ScrapingService(facebook_actor)
preparation_service = PreparationService(
    path_resolver.get_facebook_saved_base()
)

# Upload services (opcionales)
try:
    from app.services.drive_service import DriveService
    from app.services.gcs_service import GCSService
    drive_svc = DriveService()
    gcs_svc = GCSService()
    upload_service = UploadService(drive_svc, gcs_svc)
except ImportError:
    upload_service = UploadService(None, None)


async def _execute_full_workflow(
    page_url: str,
    count: int,
    top_n: int,
    bucket_name: Optional[str],
    folder_id: Optional[str]
):
    """
    Ejecuta workflow completo: scrape -> prepare -> upload.
    """
    # 1. Scraping
    scrape_result = await scraping_service.scrape_and_save(
        page_url=page_url,
        count=count
    )
    run_id = scrape_result['run_id']
    
    # 2. Esperar completación
    await scraping_service.wait_for_completion(run_id)
    
    # 3. Preparar top N
    prep_result = await preparation_service.prepare_top_n(run_id, top_n)
    
    # 4. Upload a GCS/Drive si se especifica
    if bucket_name or folder_id:
        base_path = path_resolver.get_facebook_saved_base()
        run_path = base_path / run_id
        
        if bucket_name:
            await upload_service.upload_to_gcs(
                run_path,
                bucket_name,
                run_id
            )
        
        if folder_id:
            await upload_service.upload_to_drive(
                run_path,
                folder_id,
                run_id
            )
    
    return {
        "success": True,
        "run_id": run_id,
        "scrape": scrape_result,
        "preparation": prep_result
    }
@router.post("/full")
async def execute_full_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks
):
    """
    Ejecuta workflow completo en background.

    Args:
        request: Parámetros del workflow
        background_tasks: FastAPI background tasks

    Returns:
        ID del workflow iniciado
    """
    try:
        # Ejecutar en background
        background_tasks.add_task(
            _execute_full_workflow,
            request.page_url,
            request.count,
            request.top_n,
            request.bucket_name if request.upload_to_gcs else None,
            request.folder_id if request.upload_to_drive else None
        )

        return {
            "success": True,
            "message": "Workflow iniciado en background",
            "workflow_params": request.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prepare-upload/{run_id}")
async def prepare_and_upload(
    run_id: str,
    top_n: int = 10,
    bucket_name: Optional[str] = None,
    folder_id: Optional[str] = None
):
    """
    Prepara un run existente y lo sube.
    """
    try:
        # Preparar
        prep_result = await preparation_service.prepare_top_n(run_id, top_n)
        
        if not prep_result['success']:
            raise HTTPException(
                status_code=404,
                detail=prep_result['message']
            )
        
        # Upload
        base_path = path_resolver.get_facebook_saved_base()
        run_path = base_path / run_id
        
        upload_results = {}
        
        if bucket_name:
            gcs_result = await upload_service.upload_to_gcs(
                run_path,
                bucket_name,
                run_id
            )
            upload_results['gcs'] = gcs_result
        
        if folder_id:
            drive_result = await upload_service.upload_to_drive(
                run_path,
                folder_id,
                run_id
            )
            upload_results['drive'] = drive_result
        
        return {
            "success": True,
            "run_id": run_id,
            "preparation": prep_result,
            "uploads": upload_results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))