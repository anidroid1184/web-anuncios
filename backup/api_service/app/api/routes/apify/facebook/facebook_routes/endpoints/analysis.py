"""
Facebook Routes - Endpoints de Análisis
Análisis de campañas con IA y health checks
"""

from fastapi import APIRouter, HTTPException
from ..models import AnalyzeCampaignRequest
from ..services import AnalysisService, HealthService
import os

router = APIRouter(tags=["analysis"])

# Servicios
analysis_service = AnalysisService(
    openai_api_key=os.getenv('OPENAI_API_KEY')
)

# Health service (con servicios opcionales)
try:
    from app.services.drive_service import DriveService
    from app.services.gcs_service import GCSService
    drive_svc = DriveService()
    gcs_svc = GCSService()
    health_service = HealthService(drive_svc, gcs_svc)
except ImportError:
    health_service = HealthService(None, None)


@router.post("/analyze")
async def analyze_campaign(request: AnalyzeCampaignRequest):
    """
    Analiza una campaña con IA.

    Args:
        request: Parámetros del análisis

    Returns:
        Resultado del análisis
    """
    try:
        result = await analysis_service.analyze_campaign(
            campaign_name=request.campaign_name,
            run_id=request.run_id,
            top_n=request.top_n,
            analysis_type=request.analysis_type
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{run_id}/report")
async def generate_report(
    run_id: str,
    format: str = 'pdf'
):
    """
    Genera un reporte del análisis.

    Args:
        run_id: ID del run
        format: Formato del reporte

    Returns:
        Información del reporte generado
    """
    try:
        analysis_data = {"run_id": run_id}
        result = await analysis_service.generate_report(
            analysis_data,
            format
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check de servicios.

    Returns:
        Estado de todos los servicios
    """
    try:
        result = await health_service.health_check()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug")
async def debug_info():
    """
    Información de debug del sistema.

    Returns:
        Info de debug
    """
    try:
        result = await health_service.get_debug_info()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
