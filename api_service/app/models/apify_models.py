"""
Modelos Pydantic para endpoints de Apify
Contiene schemas para actors, runs y respuestas de la API de Apify
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class ActorDetail(BaseModel):
    """Modelo para detalles completos de un actor de Apify"""
    id: str
    name: str
    username: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    stats: Optional[dict] = None
    versions: Optional[List[dict]] = None
    isPublic: Optional[bool] = None
    createdAt: Optional[str] = None
    modifiedAt: Optional[str] = None


class ActorListItem(BaseModel):
    """Modelo simplificado para items en lista de actors"""
    id: str
    name: str
    username: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class ActorListResponse(BaseModel):
    """Respuesta para endpoint de lista de actors"""
    total: int
    count: int
    offset: int
    limit: int
    items: List[ActorListItem]


class ActorRunStatus(str, Enum):
    """Estados posibles de ejecucion de un actor"""
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMING_OUT = "TIMING-OUT"
    TIMED_OUT = "TIMED-OUT"
    ABORTING = "ABORTING"
    ABORTED = "ABORTED"


class TikTokScraperInput(BaseModel):
    """Parametros de entrada para el scraper de TikTok con defaults seguros"""
    hashtags: Optional[List[str]] = Field(
        default=None,
        description="Lista de hashtags a buscar (sin el #)",
        max_length=10,
        example=["fyp", "viral"]
    )
    profiles: Optional[List[str]] = Field(
        default=None,
        description="Lista de perfiles de usuario a extraer",
        max_length=10,
        example=["@charlidamelio"]
    )
    search_queries: Optional[List[str]] = Field(
        default=None,
        description="Terminos de busqueda generales",
        max_length=5,
        example=["funny videos"]
    )
    video_urls: Optional[List[str]] = Field(
        default=None,
        description="URLs directas de videos TikTok",
        max_length=20,
        example=["https://www.tiktok.com/@user/video/123"]
    )
    max_videos: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Numero maximo de videos a extraer por fuente"
    )
    wait_for_finish: int = Field(
        default=60,
        ge=5,
        le=300,
        description="Segundos a esperar que termine la ejecucion"
    )


class TikTokVideoMetadata(BaseModel):
    """Metadata normalizada de un video de TikTok"""
    id: str = Field(description="ID unico del video")
    author_username: Optional[str] = Field(
        default=None, description="Usuario autor")
    author_name: Optional[str] = Field(
        default=None, description="Nombre del autor")
    text: Optional[str] = Field(
        default=None, description="Caption/texto del video")
    video_url: Optional[str] = Field(default=None, description="URL del video")
    cover_url: Optional[str] = Field(
        default=None, description="URL de la portada")
    play_count: Optional[int] = Field(default=0, description="Vistas")
    digg_count: Optional[int] = Field(default=0, description="Likes")
    comment_count: Optional[int] = Field(default=0, description="Comentarios")
    share_count: Optional[int] = Field(default=0, description="Compartidos")
    download_count: Optional[int] = Field(default=0, description="Descargas")
    create_time: Optional[str] = Field(
        default=None, description="Fecha creacion")
    music_title: Optional[str] = Field(
        default=None, description="Titulo musica")
    music_author: Optional[str] = Field(
        default=None, description="Autor musica")
    hashtags: Optional[List[str]] = Field(default=[], description="Hashtags")


class TikTokResponse(BaseModel):
    """Respuesta normalizada del scraper de TikTok"""
    status: str = Field(description="Estado: success, error, pending")
    run_id: Optional[str] = Field(
        default=None, description="ID ejecucion Apify")
    count: int = Field(default=0, description="Numero de videos obtenidos")
    data: List[TikTokVideoMetadata] = Field(
        default=[],
        description="Lista de videos extraidos"
    )
    message: Optional[str] = Field(
        default=None,
        description="Mensaje adicional o error"
    )
