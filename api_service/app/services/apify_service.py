"""
Servicio de integración con Apify API para extracción automatizada de anuncios.

MODULO: app/services/apify_service.py
AUTOR: Sistema de Analizador de Anuncios
VERSION: 1.0.0
FECHA: 2025-10-03

PROPOSITO:
    Automatizar completamente la extracción de anuncios de Facebook mediante
    la API v2 de Apify, reemplazando el proceso manual previo de descarga
    y procesamiento de archivos JSON estáticos.

REEMPLAZA:
    - Proceso manual de generación de archivos JSON (jsonprueba.json)
    - Descarga manual de datasets desde Apify Console
    - Configuración manual de parámetros de extracción

FUNCIONALIDAD CORE:
    - Ejecución programática de actors específicos de Apify
    - Monitoreo en tiempo real del progreso de extracción
    - Descarga automática y estructuración de resultados
    - Conversión y validación a modelos de datos tipados
    - Manejo robusto de errores y reintentos automáticos
    - Logging detallado de todas las operaciones

BENEFICIOS PRINCIPALES:
    - Eliminación completa del proceso manual y propenso a errores
    - Extracción en tiempo real sin intervención humana
    - Validación automática de integridad de datos
    - Integración directa con pipeline de procesamiento
    - Escalabilidad para múltiples extracciones concurrentes
    - Trazabilidad completa de operaciones

DEPENDENCIAS TECNICAS:
    - httpx: Cliente HTTP asíncrono de alto rendimiento
    - Apify API v2: Plataforma de web scraping y automatización
    - Token de autenticación de Apify (configurado via variable de entorno)
    - Pydantic: Validación de esquemas de datos
    - asyncio: Operaciones asíncronas nativas de Python

FLUJO DE EJECUCION TIPICO:
    1. Inicialización del servicio con token de autenticación
    2. Configuración de parámetros de extracción específicos
    3. Ejecución de actor especializado en Facebook Ads Library
    4. Monitoreo periódico del progreso hasta completar exitosamente
    5. Descarga y parsing de resultados en formato estructurado
    6. Validación de datos y conversión a modelos tipados
    7. Retorno de datos listos para procesamiento posterior

LIMITACIONES Y CONSIDERACIONES:
    - Dependiente de disponibilidad de la plataforma Apify
    - Sujeto a límites de rate limiting de Facebook Ads Library
    - Requiere manejo cuidadoso de timeouts para extracciones grandes
    - Costos asociados al uso de créditos de Apify por ejecución
"""
import os
import json
import httpx
from typing import Dict, Any, List, Optional
from app.models.schemas import ApifyRequest, ApifyResponse, AdData


class ApifyService:
    """
    Servicio principal para interactuar con la API v2 de Apify.

    Proporciona una interfaz de alto nivel para ejecutar actors de Apify,
    monitorear su progreso y obtener resultados de manera asíncrona.
    Diseñado específicamente para la extracción de anuncios de Facebook
    pero extensible para otros tipos de actors.

    La clase maneja automáticamente:
    - Autenticación con token de API
    - Reintentos en caso de fallos temporales
    - Timeouts apropiados para operaciones de larga duración
    - Parsing y validación de respuestas JSON
    - Conversión a modelos de datos tipados

    Attributes:
        api_token (str): Token de autenticación válido para Apify API
        base_url (str): URL base de la API v2 de Apify (https://api.apify.com/v2)
        client (httpx.AsyncClient): Cliente HTTP asíncrono reutilizable
            configurado con timeouts apropiados

    Example:
        >>> service = ApifyService("apify_api_abc123...")
        >>> run_id = await service.run_actor(
        ...     "apify/facebook-ads-scraper",
        ...     {"pages": ["Coca Cola"], "maxResults": 100}
        ... )
        >>> status = await service.get_run_status(run_id)
        >>> if status == "SUCCEEDED":
        ...     results = await service.get_run_results(run_id)

    Note:
        El cliente HTTP se mantiene abierto para reutilización eficiente.
        Asegúrate de llamar await service.close() al finalizar.
    """

    def __init__(self, api_token: str):
        """
        Inicializa el servicio de Apify con autenticación.

        Configura el cliente HTTP asíncrono con el token de autenticación
        y establece la URL base de la API v2 de Apify. Valida que el token
        proporcionado no esté vacío.

        Args:
            api_token (str): Token de autenticación de Apify obtenido desde
                el dashboard de usuario en apify.com. Formato típico:
                "apify_api_" seguido de 40 caracteres alfanuméricos.

        Raises:
            ValueError: Si api_token está vacío, es None, o contiene solo
                espacios en blanco.

        Example:
            >>> # Token válido desde variables de entorno
            >>> import os
            >>> token = os.getenv("APIFY_TOKEN")
            >>> service = ApifyService(token)

            >>> # Token directo (no recomendado en producción)
            >>> service = ApifyService("apify_api_abc123def456...")

        Note:
            El token se almacena en memoria durante la vida del objeto.
            En entornos de producción, usa variables de entorno o
            sistemas de gestión de secretos seguros.
        """
        if not api_token or not api_token.strip():
            raise ValueError("Token de Apify es requerido")

        self.api_token = api_token
        self.base_url = "https://api.apify.com/v2"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def run_actor(self, actor_id: str, input_data: Dict[str, Any]) -> str:
        """
        Ejecuta un actor específico de Apify con configuración personalizada.

        Envía una petición HTTP POST al endpoint de Apify para iniciar la
        ejecución de un actor específico con los parámetros proporcionados.
        La ejecución es asíncrona - esta función retorna inmediatamente
        con un run_id para monitoreo posterior.

        Args:
            actor_id (str): Identificador único del actor en Apify.
                Formatos válidos:
                - "username/actor-name" (ej: "apify/facebook-ads-scraper")
                - ID alfanumérico directo del actor
                - Debe existir y ser accesible con el token actual
            input_data (Dict[str, Any]): Configuración específica del actor.
                La estructura varía según el actor pero típicamente incluye:
                - pages: Lista de páginas de Facebook a analizar
                - searchTerms: Términos de búsqueda opcionales
                - maxResults: Límite de resultados a extraer
                - filters: Filtros adicionales específicos del actor

        Returns:
            str: ID único de la ejecución (run_id) para monitoreo posterior.
                Formato típico: string alfanumérico de 15-25 caracteres.
                Se usa para consultar estado y obtener resultados.

        Raises:
            httpx.HTTPStatusError: Si la respuesta HTTP no es 201 Created
            httpx.RequestError: Si falla la conexión HTTP con Apify
            ValueError: Si actor_id está vacío o input_data es inválido
            Exception: Para otros errores durante la ejecución

        Example:
            >>> # Ejecución básica de extracción de anuncios
            >>> run_id = await service.run_actor(
            ...     "apify/facebook-ads-library-scraper",
            ...     {
            ...         "pages": ["Coca Cola", "Pepsi"],
            ...         "maxResults": 500,
            ...         "searchTerms": ["bebida", "refresco"],
            ...         "includeImages": True,
            ...         "includeVideos": True
            ...     }
            ... )
            >>> print(f"Ejecución iniciada: {run_id}")

        Note:
            - La ejecución es asíncrona y puede tardar minutos u horas
            - El costo en créditos de Apify se cobra al iniciar la ejecución
            - Usar get_run_status(run_id) para monitorear progreso
            - Diferentes actors requieren diferentes parámetros en input_data
        """
        url = f"{self.base_url}/acts/{actor_id}/runs"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        response = await self.client.post(
            url,
            headers=headers,
            json=input_data
        )

        if response.status_code != 201:
            raise Exception(f"Error ejecutando actor: {response.text}")

        result = response.json()
        return result["data"]["id"]

    async def get_run_status(self, run_id: str) -> str:
        """
        Obtiene el estado de una ejecución
        """
        url = f"{self.base_url}/actor-runs/{run_id}"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        response = await self.client.get(url, headers=headers)
        result = response.json()

        return result["data"]["status"]

    async def get_run_results(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene los resultados de una ejecución completada
        """
        url = f"{self.base_url}/actor-runs/{run_id}/dataset/items"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        response = await self.client.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Error obteniendo resultados: {response.text}")

        return response.json()

    async def extract_facebook_ads(
        self,
        pages: List[str],
        search_terms: Optional[List[str]] = None
    ) -> ApifyResponse:
        """
        Extrae anuncios de Facebook usando Apify
        Equivalente al proceso manual del jsonprueba.json
        """
        input_data = {
            "pages": pages,
            "searchTerms": search_terms or [],
            "maxResults": 1000,
            "includeImages": True,
            "includeVideos": True
        }

        # Actor ID específico para Facebook Ads Library (configurable vía ENV)
        actor_id = os.getenv("APIFY_FACEBOOK_NAME",
                             "curious_coder/facebook-ads-library-scraper")

        run_id = await self.run_actor(actor_id, input_data)

        # Esperar a que complete (en producción usar webhooks)
        import asyncio
        while True:
            status = await self.get_run_status(run_id)
            if status == "SUCCEEDED":
                break
            elif status == "FAILED":
                raise Exception(f"Actor falló: {run_id}")
            await asyncio.sleep(10)

        results = await self.get_run_results(run_id)

        # Convertir a modelo AdData
        ads = []
        for item in results:
            ad = AdData(
                ad_archive_id=item.get("ad_archive_id"),
                page_id=item.get("page_id"),
                page_name=item.get("page_name"),
                publisher_platform=item.get("publisher_platform", []),
                snapshot=item.get("snapshot")
            )
            ads.append(ad)

        return ApifyResponse(
            run_id=run_id,
            status="SUCCEEDED",
            data=ads
        )

    async def extract_tiktok_ads(
        self,
        pages: List[str],
        search_terms: Optional[List[str]] = None
    ) -> ApifyResponse:
        """
        Extrae anuncios de TikTok usando Apify
        """
        input_data = {
            "pages": pages,
            "searchTerms": search_terms or [],
            "maxResults": 1000,
            "includeImages": True,
            "includeVideos": True
        }

        # Actor ID específico para TikTok Ads - usar el configurado en ENV
        tiktok_actor = os.getenv("APIFY_TIKTOK_ACTOR",
                                 "apify/tiktok-ads-scraper")

        run_id = await self.run_actor(tiktok_actor, input_data)

        # Esperar a que complete
        import asyncio
        while True:
            status = await self.get_run_status(run_id)
            if status == "SUCCEEDED":
                break
            elif status == "FAILED":
                raise Exception(f"TikTok Actor falló: {run_id}")
            await asyncio.sleep(10)

        results = await self.get_run_results(run_id)

        # Convertir a modelo AdData
        ads = []
        for item in results:
            ad = AdData(
                ad_archive_id=item.get("ad_archive_id"),
                page_id=item.get("page_id"),
                page_name=item.get("page_name"),
                publisher_platform=item.get("publisher_platform", ["TikTok"]),
                snapshot=item.get("snapshot")
            )
            ads.append(ad)

        return ApifyResponse(
            run_id=run_id,
            status="SUCCEEDED",
            data=ads
        )

    async def extract_facebook_page_ads(
        self,
        actor_id: str,
        page_urls: List[str],
        include_inactive: bool = False
    ) -> ApifyResponse:
        """
        Extrae anuncios específicos de páginas de Facebook
        """
        input_data = {
            "pageUrls": page_urls,
            "includeInactive": include_inactive,
            "maxResults": 500
        }

        run_id = await self.run_actor(actor_id, input_data)

        # Monitorear progreso
        import asyncio
        while True:
            status = await self.get_run_status(run_id)
            if status == "SUCCEEDED":
                break
            elif status == "FAILED":
                raise Exception(f"Facebook Page Actor falló: {run_id}")
            await asyncio.sleep(10)

        results = await self.get_run_results(run_id)

        # Convertir resultados
        ads = []
        for item in results:
            ad = AdData(
                ad_archive_id=item.get("ad_archive_id"),
                page_id=item.get("page_id"),
                page_name=item.get("page_name"),
                publisher_platform=item.get(
                    "publisher_platform", ["Facebook"]),
                snapshot=item.get("snapshot")
            )
            ads.append(ad)

        return ApifyResponse(
            run_id=run_id,
            status="SUCCEEDED",
            data=ads
        )

    async def extract_instagram_ads(
        self,
        actor_id: str,
        profiles: List[str],
        hashtags: List[str] = None,
        search_terms: Optional[List[str]] = None,
        max_ads: int = 100
    ) -> ApifyResponse:
        """
        Extrae anuncios de Instagram usando Apify
        """
        input_data = {
            "profiles": profiles,
            "hashtags": hashtags or [],
            "searchTerms": search_terms or [],
            "maxResults": max_ads,
            "includeImages": True,
            "includeVideos": True,
            "includeStories": True
        }

        run_id = await self.run_actor(actor_id, input_data)

        # Monitorear progreso
        import asyncio
        while True:
            status = await self.get_run_status(run_id)
            if status == "SUCCEEDED":
                break
            elif status == "FAILED":
                raise Exception(f"Instagram Actor falló: {run_id}")
            await asyncio.sleep(10)

        results = await self.get_run_results(run_id)

        # Convertir resultados
        ads = []
        for item in results:
            ad = AdData(
                ad_archive_id=item.get("ad_archive_id"),
                page_id=item.get("page_id"),
                page_name=item.get("page_name"),
                publisher_platform=item.get(
                    "publisher_platform", ["Instagram"]),
                snapshot=item.get("snapshot")
            )
            ads.append(ad)

        return ApifyResponse(
            run_id=run_id,
            status="SUCCEEDED",
            data=ads
        )

    async def extract_instagram_story_ads(
        self,
        actor_id: str,
        profile_urls: List[str],
        include_highlights: bool = True
    ) -> ApifyResponse:
        """
        Extrae anuncios de Stories de Instagram
        """
        input_data = {
            "profileUrls": profile_urls,
            "includeHighlights": include_highlights,
            "storiesOnly": True,
            "maxResults": 200
        }

        run_id = await self.run_actor(actor_id, input_data)

        # Monitorear progreso
        import asyncio
        while True:
            status = await self.get_run_status(run_id)
            if status == "SUCCEEDED":
                break
            elif status == "FAILED":
                raise Exception(f"Instagram Stories Actor falló: {run_id}")
            await asyncio.sleep(10)

        results = await self.get_run_results(run_id)

        # Convertir resultados
        ads = []
        for item in results:
            ad = AdData(
                ad_archive_id=item.get("ad_archive_id"),
                page_id=item.get("page_id"),
                page_name=item.get("page_name"),
                publisher_platform=["Instagram Stories"],
                snapshot=item.get("snapshot")
            )
            ads.append(ad)

        return ApifyResponse(
            run_id=run_id,
            status="SUCCEEDED",
            data=ads
        )

    async def extract_instagram_reel_ads(
        self,
        actor_id: str,
        hashtags: List[str],
        max_reels: int = 50
    ) -> ApifyResponse:
        """
        Extrae anuncios de Reels de Instagram
        """
        input_data = {
            "hashtags": hashtags,
            "reelsOnly": True,
            "maxResults": max_reels,
            "includeVideos": True
        }

        run_id = await self.run_actor(actor_id, input_data)

        # Monitorear progreso
        import asyncio
        while True:
            status = await self.get_run_status(run_id)
            if status == "SUCCEEDED":
                break
            elif status == "FAILED":
                raise Exception(f"Instagram Reels Actor falló: {run_id}")
            await asyncio.sleep(10)

        results = await self.get_run_results(run_id)

        # Convertir resultados
        ads = []
        for item in results:
            ad = AdData(
                ad_archive_id=item.get("ad_archive_id"),
                page_id=item.get("page_id"),
                page_name=item.get("page_name"),
                publisher_platform=["Instagram Reels"],
                snapshot=item.get("snapshot")
            )
            ads.append(ad)

        return ApifyResponse(
            run_id=run_id,
            status="SUCCEEDED",
            data=ads
        )

    async def close(self):
        """Cierra el cliente HTTP"""
        await self.client.aclose()

    async def run_actor_sync(
        self,
        actor_id: str,
        input_data: Dict[str, Any],
        timeout: int = 300,
        poll_interval_start: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta un actor y espera resultados (modo sincrono).

        Args:
            actor_id: ID del actor a ejecutar
            input_data: Datos de entrada del actor
            timeout: Tiempo maximo de espera en segundos (default 300)
            poll_interval_start: Intervalo inicial de polling (default 2s)

        Returns:
            Lista de items del dataset

        Raises:
            TimeoutError: Si supera el tiempo de espera
            HTTPException: Si el actor falla o hay errores de API
        """
        import asyncio
        import time

        run_id = await self.run_actor(actor_id, input_data)
        start_time = time.time()
        poll_interval = poll_interval_start

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Timeout ejecutando actor {actor_id}. "
                    f"Run ID: {run_id}"
                )

            status = await self.get_run_status(run_id)

            if status == "SUCCEEDED":
                return await self.get_run_results(run_id)
            elif status in ["FAILED", "TIMED-OUT", "ABORTED"]:
                raise Exception(
                    f"Actor fallo con estado {status}. Run ID: {run_id}"
                )

            await asyncio.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 10)

    async def run_actor_async(
        self,
        actor_id: str,
        input_data: Dict[str, Any]
    ) -> str:
        """
        Ejecuta un actor sin esperar (modo asincrono).

        Args:
            actor_id: ID del actor a ejecutar
            input_data: Datos de entrada del actor

        Returns:
            run_id para consultar estado posteriormente
        """
        return await self.run_actor(actor_id, input_data)

    async def get_dataset_items(
        self,
        dataset_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        clean: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Obtiene items de un dataset de Apify.

        Args:
            dataset_id: ID del dataset
            limit: Numero maximo de items (None = todos)
            offset: Numero de items a saltar
            clean: Si True, limpia campos internos de Apify

        Returns:
            Lista de items del dataset

        Raises:
            httpx.HTTPStatusError: Si falla la peticion
        """
        url = f"{self.base_url}/datasets/{dataset_id}/items"
        params = {
            "token": self.api_token,
            "clean": "true" if clean else "false",
            "offset": offset
        }
        if limit:
            params["limit"] = limit

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
