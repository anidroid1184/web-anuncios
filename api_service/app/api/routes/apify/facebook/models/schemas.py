"""
Pydantic models and schemas for Facebook routes
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, AnyUrl
from pydantic import model_validator


class UrlItem(BaseModel):
    url: AnyUrl = Field(
        ...,
        description="URL de búsqueda de Facebook/Meta",
    )


class ScrapePageAds(BaseModel):
    activeStatus: Optional[str] = Field(default="all")
    countryCode: Optional[str] = Field(default="ALL")


class FacebookScraperInput(BaseModel):
    """
    Input esperado por el actor (formato cerrado)
    """
    count: int = Field(default=100, ge=1)
    scrapeAdDetails: bool = Field(default=True)
    scrapePageAds: Optional[ScrapePageAds] = Field(
        default_factory=ScrapePageAds,
    )
    urls: List[UrlItem] = Field(...)

    @model_validator(mode="after")
    def ensure_urls_present(self):
        if not self.urls or len(self.urls) == 0:
            raise ValueError("'urls' debe tener al menos 1 elemento")
        return self


class SimpleScrapeRequest(BaseModel):
    """Simple scrape request with URL and basic options"""
    url: AnyUrl = Field(..., description="URL de Ads Library a scrapear")
    count: Optional[int] = Field(default=100, ge=1)
    timeout: Optional[int] = Field(
        default=600, ge=10,
        description="Timeout máximo en segundos para esperar al run"
    )


class FacebookStartResponse(BaseModel):
    """Respuesta al iniciar el scraper"""
    status: str
    run_id: str
    message: str


class FacebookResponse(BaseModel):
    """Respuesta del scraper de Facebook"""
    status: str
    run_id: Optional[str] = None
    actor_status: Optional[str] = None
    count: int
    data: List[Dict]
    message: Optional[str] = None


class AnalyzeCampaignRequest(BaseModel):
    """Request para análisis completo de campaña con IA

    Simplemente pega la URL de Facebook Ads Library y opcionalmente
    personaliza el prompt de análisis.
    """
    url: str = Field(
        ...,
        description="URL de Facebook Ads Library a analizar"
    )
    custom_prompt: Optional[str] = Field(
        None,
        description="Prompt personalizado para el análisis. "
                    "Si no se especifica, usa la variable PROMPT del .env o "
                    "el prompt por defecto."
    )
    count: Optional[int] = Field(
        default=100,
        ge=1,
        le=200,
        description="Cantidad máxima de anuncios a scrapear (default: 100)"
    )
    top: Optional[int] = Field(
        default=10,
        ge=1,
        le=50,
        description="Cantidad de mejores anuncios a analizar con IA (default: 10)"
    )
