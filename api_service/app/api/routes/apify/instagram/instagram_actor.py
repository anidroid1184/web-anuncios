"""
Instagram Actor - Logica de interaccion con el actor de Apify para Instagram
Usa el cliente oficial ApifyClient para simplificar la comunicacion
"""

import os
from typing import Dict, List, Optional
from apify_client import ApifyClient


class InstagramActor:
    """
    Clase que encapsula toda la logica de interaccion con el actor de Instagram
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
        # Usar APIFY_INSTAGRAM_ACTOR que es la variable definida en .env
        self.actor_id = os.getenv(
            "APIFY_INSTAGRAM_ACTOR",
            "apify/instagram-scraper"
        )
        self.client = ApifyClient(token)

    async def __aenter__(self):
        """Context manager para compatibilidad con codigo existente"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager - no necesita cerrar conexiones"""
        pass

    def build_actor_input(
        self,
        usernames: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        max_posts: int = 100
    ) -> Dict:
        """
        Construye el input del actor segun los parametros proporcionados

        Args:
            usernames: Lista de usernames de Instagram
            hashtags: Lista de hashtags
            max_posts: Cantidad maxima de posts

        Returns:
            Diccionario con el input formateado para el actor
        """
        actor_input = {
            "resultsLimit": max_posts
        }

        if usernames:
            actor_input["usernames"] = usernames
        if hashtags:
            actor_input["hashtags"] = hashtags

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

        status = run_data.get("status")

        if status not in ["SUCCEEDED"]:
            raise ValueError(
                f"Run no completado. Estado actual: {status}"
            )

        dataset_id = run_data.get("defaultDatasetId")
        if not dataset_id:
            raise ValueError("El run no tiene dataset asociado")

        dataset_client = self.client.dataset(dataset_id)
        items_response = dataset_client.list_items(
            limit=limit,
            offset=offset
        )
        items = items_response.items

        return run_data, items

    @staticmethod
    def normalize_post(item: Dict) -> Dict:
        """Normaliza un post de Instagram a un formato limpio"""
        return {
            "id": item.get("id", ""),
            "username": item.get("ownerUsername"),
            "caption": item.get("caption", ""),
            "url": item.get("url", ""),
            "image_url": item.get("displayUrl"),
            "likes": item.get("likesCount", 0),
            "comments": item.get("commentsCount", 0),
            "timestamp": item.get("timestamp"),
            "is_video": item.get("isVideo", False)
        }

    @staticmethod
    def validate_input(
        usernames: Optional[List[str]],
        hashtags: Optional[List[str]]
    ) -> bool:
        """
        Valida que al menos un parametro de busqueda este presente

        Returns:
            True si hay al menos un parametro
        """
        return any([usernames, hashtags])
