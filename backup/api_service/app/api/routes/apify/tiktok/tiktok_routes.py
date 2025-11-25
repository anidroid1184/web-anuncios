"""
TikTok Routes - Endpoints para el scraper de TikTok
Usa TikTokActor para encapsular toda la logica de interaccion
Incluye endpoints para construccion de datasets
"""

from fastapi import APIRouter, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
import json

from app.models.apify_models import (
    TikTokScraperInput,
    TikTokResponse
)
from .tiktok_actor import TikTokActor

# Importar funciones de datasets
from app.processors.tiktok import (
    fetch_items_from_run,
    fetch_items_from_dataset,
    build_from_items,
    get_dataset_stats,
    SETTINGS as DATASET_SETTINGS
)

router = APIRouter(tags=["TikTok"])


# ==========================================
# MODELOS PARA ENDPOINTS DE DATASETS
# ==========================================

class DatasetBuildRequest(BaseModel):
    """Request para construir dataset desde un run o dataset ID"""
    run_id: Optional[str] = Field(
        default=None,
        description="ID del run de Apify"
    )
    dataset_id: Optional[str] = Field(
        default=None,
        description="ID del dataset de Apify"
    )
    download_images: bool = Field(
        default=True,
        description="Si descargar imagenes (avatar y cover)"
    )
    max_workers: int = Field(
        default=16,
        ge=1,
        le=64,
        description="Workers para descarga paralela"
    )


class DatasetBuildResponse(BaseModel):
    """Response de construccion de dataset"""
    status: str
    message: str
    dataset_path: str
    total_items: Optional[int] = None


class DatasetStatsResponse(BaseModel):
    """Response con estadisticas del dataset"""
    total_items: int
    date_range: dict
    engagement: dict
    content: dict
    viral_items: int
    images_downloaded: int


@router.post(
    "/scrape",
    response_model=TikTokResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def scrape_tiktok_videos(request: TikTokScraperInput):
    """
    Inicia el scraper de TikTok de forma asíncrona

    El proceso de scraping se ejecuta en segundo plano en Apify.
    Retorna inmediatamente un run_id que se usa para consultar
    el estado y los resultados posteriormente.

    Flujo recomendado:
    1. POST /scrape -> Recibe run_id (202 ACCEPTED)
    2. GET /runs/{run_id} -> Consultar estado
    3. GET /runs/{run_id}/results -> Obtener videos cuando SUCCEEDED

    Args:
        request: Parametros de busqueda (hashtags, profiles,
                 search_queries o video_urls)

    Returns:
        202 ACCEPTED: TikTokResponse con run_id para monitoreo
    """
    try:
        # Validar entrada
        if not TikTokActor.validate_input(
            request.hashtags,
            request.profiles,
            request.search_queries,
            request.video_urls
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Debe proporcionar al menos uno: hashtags, "
                    "profiles, search_queries o video_urls"
                )
            )

        # Crear actor (no requiere context manager con ApifyClient)
        actor = TikTokActor()

        # Construir input
        actor_input = actor.build_actor_input(
            hashtags=request.hashtags,
            profiles=request.profiles,
            search_queries=request.search_queries,
            video_urls=request.video_urls,
            max_videos=request.max_videos
        )

        # Iniciar actor y retornar inmediatamente
        run_data = actor.run_async(actor_input=actor_input)

        run_id = run_data.get('id')
        return TikTokResponse(
            status="started",
            run_id=run_id,
            count=0,
            data=[],
            message=(
                f"Scraping iniciado. "
                f"Consulte GET /runs/{run_id} para ver estado"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando TikTok scraper: {str(e)}"
        )


@router.get("/runs/{run_id}")
async def get_run_status_endpoint(run_id: str):
    """
    Consulta el estado de una ejecucion del actor TikTok

    Args:
        run_id: ID de la ejecucion retornado por POST /scrape

    Returns:
        Dict con estado actual del actor
        (RUNNING, SUCCEEDED, FAILED, etc)
    """
    try:
        actor = TikTokActor()
        run_data = actor.get_run_status(run_id)

        return {
            "id": run_data.get("id"),
            "status": run_data.get("status"),
            "started_at": run_data.get("startedAt"),
            "finished_at": run_data.get("finishedAt"),
            "dataset_id": run_data.get("defaultDatasetId"),
            "stats": run_data.get("stats", {})
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error consultando estado: {str(e)}"
        )


@router.get("/runs/{run_id}/results", response_model=TikTokResponse)
async def get_run_results(
    run_id: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Cantidad de resultados"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset para paginacion"
    )
):
    """
    Obtiene los resultados de una ejecucion completada del actor TikTok

    Args:
        run_id: ID de la ejecucion
        limit: Cantidad maxima de items (1-1000)
        offset: Offset para paginacion

    Returns:
        TikTokResponse con los videos scrapeados y normalizados
    """
    try:
        actor = TikTokActor()

        try:
            # Obtener resultados
            run_data, items = actor.get_results(
                run_id=run_id,
                limit=limit,
                offset=offset
            )

            # Normalizar
            normalized_data = [
                TikTokActor.normalize_video(item) for item in items
            ]

            return TikTokResponse(
                status="success",
                run_id=run_id,
                count=len(normalized_data),
                data=normalized_data
            )

        except ValueError as e:
            # Error de validacion (no tiene dataset, estado invalido)
            raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo resultados: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Verifica que el servicio TikTok este configurado correctamente
    """
    try:
        actor = TikTokActor()

        return {
            "status": "healthy",
            "service": "TikTok Scraper",
            "actor_id": actor.actor_id,
            "actor_configured": bool(actor.actor_id),
            "token_configured": bool(actor.token)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Servicio no configurado: {str(e)}"
        )


# ==========================================
# ENDPOINTS DE DATASETS
# ==========================================

@router.post(
    "/dataset/build",
    response_model=DatasetBuildResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def build_dataset(
    request: DatasetBuildRequest,
    background_tasks: BackgroundTasks
):
    """
    Construye un dataset completo desde un run o dataset de Apify

    Este endpoint descarga los items, los normaliza, calcula métricas,
    descarga imágenes (opcional) y genera archivos: parquet, csv, jsonl

    El proceso se ejecuta en background. Use GET /dataset/stats
    para verificar que se completó.

    Args:
        request: run_id o dataset_id + opciones de construcción
        background_tasks: FastAPI background tasks

    Returns:
        202 ACCEPTED: Dataset en construcción
    """
    try:
        # Validar que al menos un ID esté presente
        if not request.run_id and not request.dataset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar run_id o dataset_id"
            )

        # Asegurar directorios
        DATASET_SETTINGS.ensure_directories()

        # Función para ejecutar en background
        def build_dataset_task():
            try:
                # Descargar items
                if request.run_id:
                    items = fetch_items_from_run(
                        token=DATASET_SETTINGS.apify_token,
                        run_id=request.run_id,
                        page_size=DATASET_SETTINGS.page_size
                    )
                elif request.dataset_id:
                    items = fetch_items_from_dataset(
                        token=DATASET_SETTINGS.apify_token,
                        dataset_id=request.dataset_id,
                        page_size=DATASET_SETTINGS.page_size
                    )
                else:
                    # Este caso ya está validado antes, pero por seguridad
                    return

                # Construir dataset
                build_from_items(
                    items=items,
                    out_dir=DATASET_SETTINGS.out_dir,
                    img_dir=DATASET_SETTINGS.images_dir(),
                    max_workers=request.max_workers,
                    download_images=request.download_images
                )

            except Exception as e:
                print(f"Error construyendo dataset: {e}")

        # Agregar tarea a background
        background_tasks.add_task(build_dataset_task)

        source_id = request.run_id or request.dataset_id
        source_type = "run" if request.run_id else "dataset"

        return DatasetBuildResponse(
            status="building",
            message=(
                f"Dataset en construcción desde {source_type} {source_id}. "
                f"Use GET /dataset/stats para verificar completitud."
            ),
            dataset_path=str(DATASET_SETTINGS.out_dir)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando construcción de dataset: {str(e)}"
        )


@router.get(
    "/dataset/stats",
    response_model=DatasetStatsResponse
)
async def get_dataset_statistics():
    """
    Obtiene estadísticas del dataset construido

    Retorna métricas como total de items, engagement promedio,
    items virales, imágenes descargadas, etc.

    Returns:
        DatasetStatsResponse con todas las estadísticas
    """
    try:
        # Verificar que existe el dataset
        metadata_path = DATASET_SETTINGS.out_dir / "metadata.parquet"

        if not metadata_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Dataset no encontrado en {DATASET_SETTINGS.out_dir}. "
                    "Use POST /dataset/build primero."
                )
            )

        # Obtener estadísticas
        stats = get_dataset_stats(DATASET_SETTINGS.out_dir)

        return DatasetStatsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get("/dataset/files")
async def list_dataset_files():
    """
    Lista los archivos del dataset construido

    Returns:
        Dict con paths de archivos generados y su estado
    """
    try:
        out_dir = DATASET_SETTINGS.out_dir
        img_dir = DATASET_SETTINGS.images_dir()

        # Verificar archivos principales
        files_status = {
            "metadata.parquet": (out_dir / "metadata.parquet").exists(),
            "labels.csv": (out_dir / "labels.csv").exists(),
            "manifest.jsonl": (out_dir / "manifest.jsonl").exists(),
            "images_dir": img_dir.exists()
        }

        # Contar imágenes si el directorio existe
        image_count = 0
        if img_dir.exists():
            image_count = len(list(img_dir.glob("*.jpg")))

        return {
            "dataset_path": str(out_dir),
            "files": files_status,
            "image_count": image_count,
            "all_files_present": all(files_status.values())
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listando archivos: {str(e)}"
        )


@router.get("/dataset/sample")
async def get_dataset_sample(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Cantidad de items de muestra"
    )
):
    """
    Obtiene una muestra del dataset construido

    Args:
        limit: Cantidad de items a retornar (1-100)

    Returns:
        Lista con items de muestra del manifest.jsonl
    """
    try:
        manifest_path = DATASET_SETTINGS.out_dir / "manifest.jsonl"

        if not manifest_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset no encontrado"
            )

        # Leer muestra del manifest
        sample = []
        with open(manifest_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                sample.append(json.loads(line))

        return {
            "count": len(sample),
            "items": sample
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo muestra: {str(e)}"
        )
