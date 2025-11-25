"""
Facebook Routes - Servicio de Scraping
Encapsula toda la lógica de scraping usando FacebookActor
"""

from typing import Dict, Optional
import asyncio


class ScrapingService:
    """
    Servicio de scraping aplicando Single Responsibility Principle.
    Gestiona operaciones de scraping via FacebookActor.
    """

    def __init__(self, facebook_actor):
        """
        Inicializa el servicio con inyección de dependencias.

        Args:
            facebook_actor: Instancia de FacebookActor para interactuar
                           con Apify
        """
        self.actor = facebook_actor

    async def scrape_and_save(
        self,
        page_url: str,
        count: int = 50,
        country_code: str = "ALL",
        platform: str = "ALL",
        max_concurrency: int = 5
    ) -> Dict:
        """
        Inicia un scraping y guarda el resultado.

        Args:
            page_url: URL de la página a scrapear
            count: Número de anuncios a obtener
            country_code: Código de país para filtrar
            platform: Plataforma objetivo
            max_concurrency: Nivel de concurrencia

        Returns:
            Dict con run_id, status y mensaje
        """
        # Construir input para el actor
        scraper_input = {
            "scrapePageAds": [{
                "pageUrl": page_url,
                "countryCode": country_code,
                "platform": platform
            }],
            "count": count,
            "maxConcurrency": max_concurrency
        }

        # Iniciar el run
        run_info = await self.actor.start_run(scraper_input)
        run_id = run_info.get('id')

        return {
            "run_id": run_id,
            "status": "running",
            "message": f"Scraping iniciado para {page_url}"
        }

    async def scrape_with_full_input(self, scraper_input: Dict) -> Dict:
        """
        Scraping con input completo y personalizado.

        Args:
            scraper_input: Input completo del scraper

        Returns:
            Dict con información del run iniciado
        """
        run_info = await self.actor.start_run(scraper_input)

        return {
            "run_id": run_info.get('id'),
            "status": "running",
            "message": "Scraping iniciado con configuración personalizada"
        }

    async def get_run_status(self, run_id: str) -> Dict:
        """
        Obtiene el estado de un run en ejecución.

        Args:
            run_id: ID del run a consultar

        Returns:
            Dict con información de estado del run
        """
        status = await self.actor.get_run_status(run_id)
        return {
            "run_id": run_id,
            "status": status.get('status'),
            "details": status
        }

    async def get_run_results(
        self,
        run_id: str,
        limit: Optional[int] = None
    ) -> Dict:
        """
        Obtiene los resultados de un run completado.

        Args:
            run_id: ID del run
            limit: Límite opcional de resultados

        Returns:
            Dict con los resultados del scraping
        """
        results = await self.actor.get_run_results(run_id, limit=limit)

        return {
            "run_id": run_id,
            "total_items": len(results),
            "items": results
        }

    async def wait_for_completion(
        self,
        run_id: str,
        timeout: int = 600,
        poll_interval: int = 5
    ) -> Dict:
        """
        Espera a que un run se complete.

        Args:
            run_id: ID del run
            timeout: Timeout máximo en segundos
            poll_interval: Intervalo de polling en segundos

        Returns:
            Dict con estado final del run
        """
        elapsed = 0
        while elapsed < timeout:
            status_info = await self.get_run_status(run_id)
            status = status_info.get('status')

            if status in ['SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT']:
                return status_info

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return {
            "run_id": run_id,
            "status": "TIMEOUT",
            "message": f"Run no completó en {timeout} segundos"
        }
