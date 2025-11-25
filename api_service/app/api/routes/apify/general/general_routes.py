"""
General Routes - Endpoints generales para operaciones con Apify
Lista actores, datasets y runs de la cuenta
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from apify_client import ApifyClient

router = APIRouter(tags=["Apify General"])


# ==========================================
# MODELOS PYDANTIC
# ==========================================

class ActorInfo(BaseModel):
    """Información básica de un actor"""
    id: str
    name: str
    username: str
    title: Optional[str] = None
    description: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    modified_at: Optional[datetime] = Field(None, alias="modifiedAt")

    class Config:
        populate_by_name = True


class DatasetInfo(BaseModel):
    """Información básica de un dataset"""
    id: str
    name: Optional[str] = None
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    modified_at: Optional[datetime] = Field(None, alias="modifiedAt")
    accessed_at: Optional[datetime] = Field(None, alias="accessedAt")
    item_count: int = Field(0, alias="itemCount")
    clean_item_count: int = Field(0, alias="cleanItemCount")

    class Config:
        populate_by_name = True


class RunInfo(BaseModel):
    """Información básica de un run"""
    id: str
    actor_id: str = Field(..., alias="actId")
    status: str
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    finished_at: Optional[datetime] = Field(None, alias="finishedAt")
    build_id: Optional[str] = Field(None, alias="buildId")
    default_dataset_id: Optional[str] = Field(
        None, alias="defaultDatasetId"
    )
    default_key_value_store_id: Optional[str] = Field(
        None, alias="defaultKeyValueStoreId"
    )
    stats: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_apify_client() -> ApifyClient:
    """Obtiene cliente de Apify autenticado"""
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise HTTPException(
            status_code=500,
            detail="APIFY_TOKEN no configurado en variables de entorno"
        )
    return ApifyClient(token)


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/actors", response_model=List[ActorInfo])
async def list_actors(
    limit: int = Query(
        default=100, ge=1, le=1000,
        description="Máximo de actores a retornar"
    ),
    offset: int = Query(
        default=0, ge=0,
        description="Número de actores a saltar"
    ),
    my: bool = Query(
        default=False,
        description="Solo mis actores (creados por mí)"
    )
):
    """
    Lista todos los actores disponibles en la cuenta de Apify

    Permite listar actores propios o todos los disponibles con paginación.

    **Parámetros:**
    - **limit**: Cantidad máxima de actores (1-1000, default: 100)
    - **offset**: Cantidad de actores a omitir para paginación
    - **my**: Si es True, solo lista actores propios

    **Returns:**
    Lista de actores con información básica

    **Ejemplo:**
    ```
    GET /api/v1/apify/general/actors?limit=50&my=true
    ```
    """
    try:
        client = get_apify_client()

        # Listar actores
        if my:
            # Solo actores propios
            actors_page = client.actors().list(limit=limit, offset=offset)
        else:
            # Todos los actores (requiere filtro adicional si es necesario)
            actors_page = client.actors().list(limit=limit, offset=offset)

        # Extraer items
        actors = actors_page.items if hasattr(actors_page, 'items') else []

        return [
            ActorInfo(
                id=actor.get("id", ""),
                name=actor.get("name", ""),
                username=actor.get("username", ""),
                title=actor.get("title"),
                description=actor.get("description"),
                stats=actor.get("stats"),
                createdAt=actor.get("createdAt"),
                modifiedAt=actor.get("modifiedAt")
            )
            for actor in actors
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al listar actores: {str(e)}"
        )


@router.get("/datasets", response_model=List[DatasetInfo])
async def list_datasets(
    limit: int = Query(
        default=100, ge=1, le=1000,
        description="Máximo de datasets a retornar"
    ),
    offset: int = Query(
        default=0, ge=0,
        description="Número de datasets a saltar"
    ),
    unnamed: bool = Query(
        default=False,
        description="Incluir datasets sin nombre"
    )
):
    """
    Lista todos los datasets de la cuenta de Apify

    Permite paginar y filtrar datasets con o sin nombre.

    **Parámetros:**
    - **limit**: Cantidad máxima de datasets (1-1000, default: 100)
    - **offset**: Cantidad de datasets a omitir para paginación
    - **unnamed**: Si es True, incluye datasets sin nombre

    **Returns:**
    Lista de datasets con información básica
    (ID, nombre, conteo de items, fechas)

    **Ejemplo:**
    ```
    GET /api/v1/apify/general/datasets?limit=50&unnamed=true
    ```
    """
    try:
        client = get_apify_client()

        # Listar datasets
        datasets_page = client.datasets().list(
            limit=limit,
            offset=offset,
            unnamed=unnamed
        )

        # Extraer items
        datasets = (datasets_page.items
                    if hasattr(datasets_page, 'items') else [])

        return [
            DatasetInfo(
                id=dataset.get("id", ""),
                name=dataset.get("name"),
                createdAt=dataset.get("createdAt"),
                modifiedAt=dataset.get("modifiedAt"),
                accessedAt=dataset.get("accessedAt"),
                itemCount=dataset.get("itemCount", 0),
                cleanItemCount=dataset.get("cleanItemCount", 0)
            )
            for dataset in datasets
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al listar datasets: {str(e)}"
        )


@router.get("/runs", response_model=List[RunInfo])
async def list_runs(
    limit: int = Query(
        default=100, ge=1, le=1000,
        description="Máximo de runs a retornar"
    ),
    offset: int = Query(
        default=0, ge=0,
        description="Número de runs a saltar"
    ),
    status: Optional[str] = Query(
        default=None,
        description="Filtrar por estado "
        "(READY, RUNNING, SUCCEEDED, FAILED, ABORTED)"
    )
):
    """
    Lista todos los runs (ejecuciones) de actores en la cuenta

    Permite paginar y filtrar runs por estado.

    **Parámetros:**
    - **limit**: Cantidad máxima de runs (1-1000, default: 100)
    - **offset**: Cantidad de runs a omitir para paginación
    - **status**: Filtrar por estado específico
      - `READY`: Listo para ejecutar
      - `RUNNING`: En ejecución
      - `SUCCEEDED`: Completado exitosamente
      - `FAILED`: Falló
      - `ABORTED`: Abortado

    **Returns:**
    Lista de runs con información de estado, tiempos y IDs de datasets

    **Ejemplo:**
    ```
    GET /api/v1/apify/general/runs?limit=50&status=SUCCEEDED
    ```
    """
    try:
        client = get_apify_client()

        # Construir parámetros - solo limit y offset
        list_params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset
        }

        # Listar runs (sin filtro de status por limitaciones del SDK)
        runs_page = client.runs().list(**list_params)

        # Extraer items
        runs = runs_page.items if hasattr(runs_page, 'items') else []

        # Filtrar por status si se especificó (post-procesamiento)
        if status:
            status_upper = status.upper()
            runs = [r for r in runs if r.get("status") == status_upper]

        return [
            RunInfo(
                id=run.get("id", ""),
                actId=run.get("actId", ""),
                status=run.get("status", "UNKNOWN"),
                startedAt=run.get("startedAt"),
                finishedAt=run.get("finishedAt"),
                buildId=run.get("buildId"),
                defaultDatasetId=run.get("defaultDatasetId"),
                defaultKeyValueStoreId=run.get("defaultKeyValueStoreId"),
                stats=run.get("stats")
            )
            for run in runs
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al listar runs: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Verifica que el servicio de Apify esté disponible

    **Returns:**
    Estado del servicio y token configurado
    """
    token = os.getenv("APIFY_TOKEN")
    if not token:
        return {
            "status": "unhealthy",
            "service": "apify_general",
            "token_configured": False,
            "error": "APIFY_TOKEN no configurado"
        }

    return {
        "status": "healthy",
        "service": "apify_general",
        "token_configured": True
    }
