"""
Router para análisis y métricas
"""
from fastapi import APIRouter, HTTPException
from app.services.bigquery_service import BigQueryService
import os

router = APIRouter()

credentials_path = os.getenv(
    "GOOGLE_CREDENTIALS_PATH", "../../shared/credentials/credenciales.json")
bq_service = BigQueryService(credentials_path)


@router.get("/dashboard-metrics")
async def get_dashboard_metrics():
    """
    Obtiene métricas principales para el dashboard
    """
    try:
        # Consulta de métricas generales
        query = """
        SELECT 
            COUNT(*) as total_ads,
            COUNT(DISTINCT page_name) as unique_pages,
            MIN(start_date) as earliest_ad,
            MAX(end_date) as latest_ad
        FROM `{project}.data-externa.proveedor.ads_library_snapshot`
        """.format(project=bq_service.credentials.project_id)

        metrics = bq_service.client.query(query).to_dataframe().iloc[0]

        # Consulta de plataformas
        platform_query = """
        SELECT 
            platform,
            COUNT(*) as count
        FROM `{project}.data-externa.proveedor.ads_library_platform`
        GROUP BY platform
        ORDER BY count DESC
        """.format(project=bq_service.credentials.project_id)

        platforms = bq_service.client.query(platform_query).to_dataframe()

        return {
            "total_ads": int(metrics['total_ads']),
            "unique_pages": int(metrics['unique_pages']),
            "date_range": {
                "earliest": str(metrics['earliest_ad']),
                "latest": str(metrics['latest_ad'])
            },
            "platforms": platforms.to_dict('records')
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_trends(days: int = 30):
    """
    Obtiene tendencias de anuncios por día
    """
    try:
        query = """
        SELECT 
            DATE(start_date) as date,
            COUNT(*) as ads_count,
            COUNT(DISTINCT page_name) as unique_pages
        FROM `{project}.data-externa.proveedor.ads_library_snapshot`
        WHERE start_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        GROUP BY DATE(start_date)
        ORDER BY date DESC
        """.format(project=bq_service.credentials.project_id, days=days)

        trends = bq_service.client.query(query).to_dataframe()

        return {
            "trends": trends.to_dict('records'),
            "period_days": days
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-advertisers")
async def get_top_advertisers(limit: int = 10):
    """
    Obtiene los principales anunciantes
    """
    try:
        query = """
        SELECT 
            page_name,
            COUNT(*) as total_ads,
            COUNT(DISTINCT DATE(start_date)) as active_days
        FROM `{project}.data-externa.proveedor.ads_library_snapshot`
        WHERE page_name IS NOT NULL
        GROUP BY page_name
        ORDER BY total_ads DESC
        LIMIT {limit}
        """.format(project=bq_service.credentials.project_id, limit=limit)

        advertisers = bq_service.client.query(query).to_dataframe()

        return {
            "top_advertisers": advertisers.to_dict('records')
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
