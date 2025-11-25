"""
Facebook Routes - Modelos de datos (Schemas)
Todos los Pydantic models usados en los endpoints
"""

from pydantic import BaseModel, Field, root_validator, AnyUrl
from typing import Optional, List, Dict


class UrlItem(BaseModel):
    """URL única para scraping de página de anuncios"""
    url: str = Field(..., description="URL completa de la página")


class ScrapePageAds(BaseModel):
    """Configuración para scraping de página de ads"""
    pageUrl: str = Field(..., description="URL base de la página")
    countryCode: str = Field(default="ALL", description="Código de país")
    platform: str = Field(default="ALL", description="Plataforma objetivo")


class FacebookScraperInput(BaseModel):
    """Input completo para el scraper de Facebook Ads Library"""
    urls: Optional[List[UrlItem]] = Field(
        default=None, description="Lista de URLs")
    scrapePageAds: Optional[List[ScrapePageAds]] = Field(
        default=None,
        description="Configuración de páginas a scrapear"
    )
    count: Optional[int] = Field(
        default=300,
        ge=1,
        description="Número de anuncios a scrapear"
    )
    maxConcurrency: Optional[int] = Field(
        default=10,
        ge=1,
        le=50,
        description="Concurrencia máxima"
    )
    proxy: Optional[Dict] = Field(
        default=None, description="Configuración de proxy")

    @root_validator(pre=True)
    def check_input_sources(cls, values):
        """Valida que se proporcione al menos una fuente de datos"""
        urls = values.get('urls')
        scrape_page = values.get('scrapePageAds')
        if not urls and not scrape_page:
            raise ValueError("Debe proporcionar 'urls' o 'scrapePageAds'")
        return values


class FacebookStartResponse(BaseModel):
    """Respuesta al iniciar un run de scraping"""
    run_id: str
    status: str
    message: str


class FacebookResponse(BaseModel):
    """Respuesta genérica de operaciones de Facebook"""
    success: bool
    message: str
    data: Optional[Dict] = None


class SimpleScrapeRequest(BaseModel):
    """Request simplificado para scraping básico"""
    page_url: str = Field(..., description="URL de la página a scrapear")
    count: int = Field(default=50, ge=1, le=1000,
                       description="Número de anuncios")
    country_code: str = Field(default="ALL", description="Código de país")
    platform: str = Field(default="ALL", description="Plataforma")
    max_concurrency: int = Field(
        default=5, ge=1, le=20, description="Concurrencia")


class AnalyzeCampaignRequest(BaseModel):
    """Request para análisis de campaña con IA"""
    campaign_name: str = Field(..., description="Nombre de la campaña")
    run_id: str = Field(..., description="ID del run a analizar")
    top_n: int = Field(default=10, ge=1, le=50, description="Top N anuncios")
    analysis_type: str = Field(
        default="performance",
        description="Tipo de análisis: 'performance', 'creative', 'full'"
    )

    class Config:
        schema_extra = {
            "example": {
                "campaign_name": "Summer Campaign 2024",
                "run_id": "abc123xyz",
                "top_n": 10,
                "analysis_type": "full"
            }
        }


class WorkflowRequest(BaseModel):
    """Request para workflows complejos (scrape+prepare+upload)"""
    page_url: str = Field(..., description="URL de la página")
    count: int = Field(default=50, ge=1, description="Número de anuncios")
    top_n: int = Field(default=10, ge=1, description="Top N para preparar")
    upload_to_gcs: bool = Field(default=True, description="Subir a GCS")
    upload_to_drive: bool = Field(default=False, description="Subir a Drive")
    folder_id: Optional[str] = Field(
        default=None, description="ID folder de Drive")
    bucket_name: Optional[str] = Field(
        default=None,
        description="Nombre del bucket GCS"
    )

    class Config:
        schema_extra = {
            "example": {
                "page_url": "https://www.facebook.com/ads/library/?active_status=all&ad_type=political_and_issue_ads&country=US&view_all_page_id=123",
                "count": 100,
                "top_n": 10,
                "upload_to_gcs": True,
                "bucket_name": "my-ads-bucket"
            }
        }
