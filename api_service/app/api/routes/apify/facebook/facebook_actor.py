"""
Facebook Actor - Logica de interaccion con el actor de Apify para Facebook
Usa el cliente oficial ApifyClient para simplificar la comunicacion
"""

import os
from typing import Dict, List, Optional, TYPE_CHECKING
from apify_client import ApifyClient

if TYPE_CHECKING:
    # Intentar importar desde el nuevo paquete refactorizado
    try:
        from .facebook_routes.models import FacebookScraperInput
    except ImportError:
        # Fallback a la ubicación antigua
        from .facebook_routes import FacebookScraperInput


class FacebookActor:
    """
    Clase que encapsula toda la logica de interaccion con el actor de Facebook
    usando el cliente oficial de Apify
    """

    def __init__(self):
        """Inicializa el cliente de Apify con las credenciales"""
        token = os.getenv("APIFY_TOKEN")
        if not token:
            raise ValueError(
                "APIFY_TOKEN no configurado en variables de entorno"
            )

        self.token = token
        # Usar APIFY_FACEBOOK_NAME que tiene el formato completo
        # Preferir valor en ENV, fallback al actor official de curious_coder
        self.actor_id = os.getenv(
            "APIFY_FACEBOOK_NAME",
            "curious_coder/facebook-ads-library-scraper"
        )
        self.client = ApifyClient(token)

    async def __aenter__(self):
        """Context manager para compatibilidad con codigo existente"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager - no necesita cerrar conexiones"""
        pass

    def build_actor_input(self, request: "FacebookScraperInput") -> Dict:
        """
        Construye el input del actor según el modelo FacebookScraperInput

        Mapeará los campos al formato que el actor espera, por ejemplo:
        - count
        - scrapeAdDetails
        - scrapePageAds.activeStatus
        - scrapePageAds.countryCode
        - urls: [{"url": ...}, ...]
        """
        actor_input: Dict = {
            "count": int(getattr(request, "count", 100)),
            "scrapeAdDetails": bool(getattr(request, "scrapeAdDetails", True)),
        }

    # Añadir campos anidados como claves con punto si vienen
        spa = getattr(request, "scrapePageAds", None)
        if spa:
            if getattr(spa, "activeStatus", None) is not None:
                actor_input["scrapePageAds.activeStatus"] = spa.activeStatus
            if getattr(spa, "countryCode", None) is not None:
                actor_input["scrapePageAds.countryCode"] = spa.countryCode

        # Construir lista de URLs simple
        urls = []
        for u in getattr(request, "urls", []) or []:
            # u puede ser un dict o un objeto Pydantic; manejar ambos
            if isinstance(u, dict):
                url_val = u.get("url")
            else:
                url_val = getattr(u, "url", None)
            if url_val:
                # Enviar al actor la estructura esperada: objetos
                # con clave 'url'
                urls.append({"url": str(url_val)})

        if urls:
            actor_input["urls"] = urls

        return actor_input

    def run_actor(self, actor_input: Dict) -> Optional[Dict]:
        """
        Ejecuta el actor y espera a que termine (usa .call())

        Args:
            actor_input: Input construido para el actor

        Returns:
            Dict con informacion del run completado o None
        """
        run = self.client.actor(self.actor_id).call(run_input=actor_input)
        return run

    def run_async(self, actor_input: Dict) -> Optional[Dict]:
        """
        Inicia el actor sin esperar resultados (usa .start())

        Args:
            actor_input: Input construido para el actor

        Returns:
            Dict con informacion del run iniciado o None
        """
        run = self.client.actor(self.actor_id).start(run_input=actor_input)
        return run

    def get_run_status(self, run_id: str) -> Optional[Dict]:
        """
        Consulta el estado de una ejecucion

        Args:
            run_id: ID de la ejecucion

        Returns:
            Dict con informacion del estado actual del run o None
        """
        run = self.client.run(run_id).get()
        # ApifyClient puede devolver la estructura {'data': {...}} o el dict directo.
        if isinstance(run, dict) and 'data' in run and isinstance(run['data'], dict):
            return run['data']
        return run

    def get_results(
        self,
        run_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[Optional[Dict], List[Dict]]:
        """
        Obtiene los resultados de una ejecucion

        Args:
            run_id: ID de la ejecucion
            limit: Cantidad maxima de items
            offset: Offset para paginacion

        Returns:
            Tupla (run_data, items)

        Raises:
            ValueError: Si el run no esta completo o no tiene datos
        """
        run_data = self.client.run(run_id).get()
        if not run_data:
            raise ValueError("No se pudo obtener informacion del run")

        # Normalizar estructura: algunos endpoints devuelven {'data': {...}}
        if isinstance(run_data, dict) and 'data' in run_data and isinstance(run_data['data'], dict):
            rd = run_data['data']
        else:
            rd = run_data

        status = rd.get("status")

        if status not in ["SUCCEEDED"]:
            raise ValueError(
                f"Run no completado. Estado actual: {status}"
            )

        dataset_id = rd.get("defaultDatasetId") or rd.get('defaultDatasetId')
        if not dataset_id:
            # Algunos actores devuelven 'defaultDatasetId' dentro de 'data' u otras claves
            raise ValueError("El run no tiene dataset asociado")

        dataset_client = self.client.dataset(dataset_id)
        items_response = dataset_client.list_items(
            limit=limit,
            offset=offset
        )

        # items_response puede ser un objeto con atributo .items o una lista/dict
        if hasattr(items_response, 'items'):
            items = items_response.items
        elif isinstance(items_response, list):
            items = items_response
        elif isinstance(items_response, dict) and 'items' in items_response:
            items = items_response['items']
        else:
            items = []

        return rd, items

    @staticmethod
    def normalize_ad(item: Dict) -> Dict:
        """
        Normaliza un item del dataset a un formato limpio

        Mapea los campos del Facebook Ads Library Scraper al formato
        esperado. El scraper retorna campos con notación de punto como
        "snapshot.body.text"

        Args:
            item: Item crudo del dataset de Apify

        Returns:
            Diccionario con datos normalizados del anuncio
        """
        return {
            "id": item.get("ad_archive_id", ""),
            "adArchiveID": item.get("ad_archive_id", ""),
            "pageID": "",  # No disponible directamente
            "pageName": item.get("snapshot.page_name", ""),
            "adCreativeBody": item.get("snapshot.body.text", ""),
            "adCreativeLinkCaption": item.get("snapshot.caption", ""),
            "adCreativeLinkDescription": item.get(
                "snapshot.link_description", ""
            ),
            "adCreativeLinkTitle": item.get("snapshot.title", ""),
            "adSnapshotURL": "",  # No disponible en el formato actual
            "startDate": str(item.get("start_date", "")),
            "endDate": str(item.get("end_date", "")),
            "currency": "",  # No disponible directamente
            "adSpend": {},  # No disponible en formato básico
            "adImpressions": {},  # No disponible en formato básico
            "mediaType": "",  # Podría inferirse de los campos disponibles
            "videoURL": "",  # No disponible en formato básico
            "imageURL": "",  # No disponible en formato básico
            # Campos adicionales útiles del scraper
            "ctaText": item.get("snapshot.cta_text", ""),
            "linkUrl": item.get("snapshot.link_url", ""),
            "pageProfilePictureUrl": item.get(
                "snapshot.page_profile_picture_url", ""
            ),
            "pageProfileUri": item.get("snapshot.page_profile_uri", ""),
        }
