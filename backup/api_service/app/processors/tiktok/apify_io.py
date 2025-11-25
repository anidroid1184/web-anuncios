"""
Módulo para descargar items de datasets de Apify
Utiliza el cliente oficial ApifyClient con paginación automática
"""
from __future__ import annotations
from typing import List, Dict, Any
from tqdm import tqdm
from apify_client import ApifyClient


def fetch_items_from_dataset(
    token: str,
    dataset_id: str,
    page_size: int = 1000,
    clean: bool = True
) -> List[Dict[str, Any]]:
    """
    Descarga TODOS los items de un dataset de Apify usando paginación

    Args:
        token: Token de autenticación de Apify
        dataset_id: ID del dataset a descargar
        page_size: Cantidad de items por página (máximo 1000)
        clean: Si True, omite items vacíos y campos ocultos

    Returns:
        Lista de todos los items del dataset

    Raises:
        ValueError: Si el token o dataset_id están vacíos

    Example:
        >>> items = fetch_items_from_dataset(
        ...     token="apify_api_...",
        ...     dataset_id="abc123...",
        ...     page_size=1000
        ... )
        >>> print(f"Descargados {len(items)} items")
    """
    if not token:
        raise ValueError("El token de Apify es requerido")
    if not dataset_id:
        raise ValueError("El dataset_id es requerido")

    # Inicializar cliente
    client = ApifyClient(token)
    dataset_client = client.dataset(dataset_id)

    # Descargar items con paginación
    items: List[Dict[str, Any]] = []
    offset = 0

    with tqdm(desc="Descargando items de Apify", unit="item") as pbar:
        while True:
            # Obtener página actual
            page = dataset_client.list_items(
                limit=page_size,
                offset=offset,
                clean=clean
            )
            batch = page.items

            # Agregar items a la lista
            items.extend(batch)
            pbar.update(len(batch))

            # Si la página tiene menos items que el límite, terminamos
            if len(batch) < page_size:
                break

            offset += page_size

    return items


def fetch_items_from_run(
    token: str,
    run_id: str,
    page_size: int = 1000,
    clean: bool = True
) -> List[Dict[str, Any]]:
    """
    Descarga TODOS los items del dataset generado por un run de Apify

    Args:
        token: Token de autenticación de Apify
        run_id: ID del run cuyo dataset queremos descargar
        page_size: Cantidad de items por página (máximo 1000)
        clean: Si True, omite items vacíos y campos ocultos

    Returns:
        Lista de todos los items del dataset del run

    Raises:
        ValueError: Si el run no tiene dataset asociado

    Example:
        >>> items = fetch_items_from_run(
        ...     token="apify_api_...",
        ...     run_id="xyz789...",
        ...     page_size=1000
        ... )
    """
    if not token:
        raise ValueError("El token de Apify es requerido")
    if not run_id:
        raise ValueError("El run_id es requerido")

    # Inicializar cliente
    client = ApifyClient(token)

    # Obtener información del run
    run_data = client.run(run_id).get()
    if not run_data:
        raise ValueError(f"No se encontró el run {run_id}")

    # Obtener el dataset_id del run
    dataset_id = run_data.get("defaultDatasetId")
    if not dataset_id:
        raise ValueError(
            f"El run {run_id} no tiene dataset asociado"
        )

    # Descargar items del dataset
    return fetch_items_from_dataset(
        token=token,
        dataset_id=dataset_id,
        page_size=page_size,
        clean=clean
    )
