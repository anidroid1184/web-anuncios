"""
Servicio para integración con la API FastAPI
"""
import httpx
from django.conf import settings
from typing import Dict, Any, Optional, List


class APIService:
    """
    Cliente para interactuar con el servicio de APIs FastAPI
    """

    def __init__(self):
        self.base_url = settings.API_SERVICE_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas del dashboard desde la API
        """
        response = await self.client.get(
            f"{self.base_url}/api/v1/analytics/dashboard-metrics"
        )
        response.raise_for_status()
        return response.json()

    async def get_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Obtiene tendencias de anuncios
        """
        response = await self.client.get(
            f"{self.base_url}/api/v1/analytics/trends",
            params={"days": days}
        )
        response.raise_for_status()
        return response.json()

    async def get_top_advertisers(self, limit: int = 10) -> Dict[str, Any]:
        """
        Obtiene principales anunciantes
        """
        response = await self.client.get(
            f"{self.base_url}/api/v1/analytics/top-advertisers",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()

    async def extract_ads_from_apify(
        self,
        pages: List[str],
        search_terms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Solicita extracción de anuncios via Apify
        """
        data = {
            "actor_id": "facebook-ads-library",
            "input_data": {
                "pages": pages,
                "search_terms": search_terms or []
            }
        }

        response = await self.client.post(
            f"{self.base_url}/api/v1/apify/extract-ads",
            json=data
        )
        response.raise_for_status()
        return response.json()

    async def load_data_to_bigquery(self, ads_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Carga datos procesados a BigQuery
        """
        response = await self.client.post(
            f"{self.base_url}/api/v1/bigquery/load-data",
            json=ads_data
        )
        response.raise_for_status()
        return response.json()

    async def upload_media_to_drive(
        self,
        ads_data: List[Dict[str, Any]],
        folder_id: str
    ) -> Dict[str, Any]:
        """
        Sube archivos de medios a Google Drive
        """
        response = await self.client.post(
            f"{self.base_url}/api/v1/drive/batch-upload",
            json={"ads_data": ads_data, "folder_id": folder_id}
        )
        response.raise_for_status()
        return response.json()

    async def get_analytics(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page_names: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene análisis de datos de BigQuery
        """
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if page_names:
            params["page_names"] = page_names

        response = await self.client.get(
            f"{self.base_url}/api/v1/bigquery/analytics",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """
        Cierra el cliente HTTP
        """
        await self.client.aclose()
