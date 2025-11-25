"""
Instagram Routes - Endpoints para el scraper de Instagram
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from .instagram_actor import InstagramActor

router = APIRouter(tags=["Instagram"])


class InstagramScraperInput(BaseModel):
    """Input para el scraper de Instagram"""
    usernames: Optional[List[str]] = Field(
        default=None,
        description="Lista de usernames de Instagram"
    )
    hashtags: Optional[List[str]] = Field(
        default=None,
        description="Lista de hashtags"
    )
    max_posts: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Cantidad maxima de posts"
    )


class InstagramStartResponse(BaseModel):
    """Respuesta al iniciar el scraper"""
    status: str
    run_id: str
    message: str


class InstagramResponse(BaseModel):
    """Respuesta del scraper de Instagram"""
    status: str
    run_id: Optional[str] = None
    actor_status: Optional[str] = None
    count: int
    data: List[Dict]
    message: Optional[str] = None


@router.post("/scrape", status_code=202)
def scrape_instagram(request: InstagramScraperInput):
    """
    Inicia el scraper de Instagram (asíncrono)
    Retorna inmediatamente con run_id para consultar estado después
    """
    try:
        # Validar input
        if not InstagramActor.validate_input(
            request.usernames,
            request.hashtags
        ):
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar usernames o hashtags"
            )

        actor = InstagramActor()

        # Construir input
        actor_input = actor.build_actor_input(
            usernames=request.usernames,
            hashtags=request.hashtags,
            max_posts=request.max_posts
        )

        # Iniciar actor asíncrono
        run_data = actor.run_async(actor_input=actor_input)

        if not run_data or not run_data.get("id"):
            raise HTTPException(
                status_code=500,
                detail="No se pudo iniciar el actor"
            )

        run_id = run_data.get("id", "")

        return InstagramStartResponse(
            status="started",
            run_id=run_id,
            message=(
                f"Actor iniciado. "
                f"Use GET /runs/{run_id} para consultar estado"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}")
def get_run_status(run_id: str):
    """Consulta el estado de una ejecución"""
    try:
        actor = InstagramActor()
        run_data = actor.get_run_status(run_id)

        if not run_data:
            raise HTTPException(
                status_code=404,
                detail=f"Run {run_id} no encontrado"
            )

        return {
            "run_id": run_id,
            "status": run_data.get("status"),
            "started_at": run_data.get("startedAt"),
            "finished_at": run_data.get("finishedAt"),
            "default_dataset_id": run_data.get("defaultDatasetId")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}/results")
def get_run_results(
    run_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """Obtiene los resultados de una ejecución completada"""
    try:
        actor = InstagramActor()

        try:
            run_data, items = actor.get_results(
                run_id=run_id,
                limit=limit,
                offset=offset
            )

            # Normalizar datos
            normalized_data = [
                InstagramActor.normalize_post(item) for item in items
            ]

            return InstagramResponse(
                status="success",
                run_id=run_id,
                actor_status=run_data.get("status") if run_data else None,
                count=len(normalized_data),
                data=normalized_data
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health_check():
    """Verifica la configuración del servicio"""
    try:
        actor = InstagramActor()
        return {
            "status": "healthy",
            "service": "Instagram Scraper",
            "actor_id": actor.actor_id,
            "configured": bool(actor.actor_id and actor.token)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
