"""
TikTok Actor - Logica de interaccion con el actor de Apify para TikTok
Usa el cliente oficial ApifyClient para simplificar la comunicacion
"""

import os
from typing import Dict, List, Optional
from apify_client import ApifyClient


class TikTokActor:
    """
    Clase que encapsula toda la logica de interaccion con el actor de TikTok
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
        # Usar APIFY_TIKTOK_NAME que tiene el formato completo
        # clockworks/tiktok-scraper
        self.actor_id = os.getenv(
            "APIFY_TIKTOK_NAME",
            "clockworks/tiktok-scraper"
        )
        self.client = ApifyClient(token)

    async def __aenter__(self):
        """Context manager para compatibilidad con codigo existente"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager - no necesita cerrar conexiones con el cliente oficial"""
        pass

    def build_actor_input(
        self,
        hashtags: Optional[List[str]] = None,
        profiles: Optional[List[str]] = None,
        search_queries: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
        max_videos: int = 100
    ) -> Dict:
        """
        Construye el input del actor segun los parametros proporcionados

        Args:
            hashtags: Lista de hashtags a buscar
            profiles: Lista de perfiles a extraer
            search_queries: Terminos de busqueda
            video_urls: URLs directas de videos
            max_videos: Cantidad maxima de videos

        Returns:
            Diccionario con el input formateado para el actor
        """
        actor_input = {
            "resultsPerPage": max_videos
        }

        if hashtags:
            actor_input["hashtags"] = hashtags
        if profiles:
            actor_input["profiles"] = profiles
        if search_queries:
            actor_input["searchQueries"] = search_queries
        if video_urls:
            actor_input["postURLs"] = video_urls

        return actor_input

    def run_actor(self, actor_input: Dict) -> Dict:
        """
        Ejecuta el actor y espera a que termine (usa .call())

        El metodo .call() del cliente de Apify:
        - Inicia el actor
        - Espera automaticamente a que termine
        - Reintenta si hay errores temporales
        - Retorna la informacion del run completado

        Args:
            actor_input: Input construido para el actor

        Returns:
            Dict con informacion del run completado (incluye status,
            defaultDatasetId, etc.)
        """
        run = self.client.actor(self.actor_id).call(run_input=actor_input)
        return run

    def run_async(self, actor_input: Dict) -> Dict:
        """
        Inicia el actor sin esperar resultados (usa .start())

        Args:
            actor_input: Input construido para el actor

        Returns:
            Dict con informacion del run iniciado (incluye id para consultar)
        """
        run = self.client.actor(self.actor_id).start(run_input=actor_input)
        return run

    def get_run_status(self, run_id: str) -> Dict:
        """
        Consulta el estado de una ejecucion

        Args:
            run_id: ID de la ejecucion

        Returns:
            Dict con informacion del estado actual del run
        """
        run = self.client.run(run_id).get()
        return run

    def get_results(
        self,
        run_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[Dict, List[Dict]]:
        """
        Obtiene los resultados de una ejecucion

        Args:
            run_id: ID de la ejecucion
            limit: Cantidad maxima de items
            offset: Offset para paginacion

        Returns:
            Tupla (run_data, items) con informacion del run y resultados

        Raises:
            ValueError: Si el run no tiene dataset o no esta completo
        """
        # Obtener informacion del run
        run_data = self.client.run(run_id).get()
        status = run_data.get("status")

        if status not in ["SUCCEEDED"]:
            raise ValueError(
                f"Run no completado. Estado actual: {status}"
            )

        # Obtener dataset ID
        dataset_id = run_data.get("defaultDatasetId")
        if not dataset_id:
            raise ValueError("El run no tiene dataset asociado")

        # Obtener items del dataset
        dataset_client = self.client.dataset(dataset_id)
        items_response = dataset_client.list_items(
            limit=limit,
            offset=offset
        )
        items = items_response.items

        return run_data, items

    @staticmethod
    def normalize_video(item: Dict):
        """
        Normaliza un item del dataset a un formato limpio y consistente

        Args:
            item: Item raw del dataset de Apify

        Returns:
            TikTokVideoMetadata con datos normalizados del video
        """
        from app.models.apify_models import TikTokVideoMetadata

        return TikTokVideoMetadata(
            id=item.get("id", ""),
            author_username=item.get("authorMeta", {}).get("name"),
            author_name=item.get("authorMeta", {}).get("nickName"),
            text=item.get("text", ""),
            video_url=item.get("videoUrl", ""),
            cover_url=item.get("covers", {}).get("default"),
            play_count=item.get("playCount", 0),
            digg_count=item.get("diggCount", 0),
            comment_count=item.get("commentCount", 0),
            share_count=item.get("shareCount", 0),
            create_time=item.get("createTime"),
            music_title=item.get("musicMeta", {}).get("musicName"),
            music_author=item.get("musicMeta", {}).get("musicAuthor"),
            hashtags=[tag.get("name") for tag in item.get("hashtags", [])]
        )

    @staticmethod
    def validate_input(
        hashtags: Optional[List[str]],
        profiles: Optional[List[str]],
        search_queries: Optional[List[str]],
        video_urls: Optional[List[str]]
    ) -> bool:
        """
        Valida que al menos un parametro de busqueda este presente

        Returns:
            True si hay al menos un parametro, False en caso contrario
        """
        return any([hashtags, profiles, search_queries, video_urls])
