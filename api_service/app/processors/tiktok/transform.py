"""
Módulo de transformación y normalización de items de TikTok
Incluye cálculo de métricas como Engagement Rate
"""
from __future__ import annotations
import math
import re
from typing import Dict, Any, Optional
from dateutil import parser as dtp
from .schema import dotted_get, extract_hashtags, extract_mentions


# Regex para detectar URLs
URL_RE = re.compile(r"^https?://", re.I)


def to_float(x: Any) -> float:
    """
    Convierte un valor a float, retornando NaN si falla

    Args:
        x: Valor a convertir

    Returns:
        Valor como float o math.nan
    """
    try:
        return float(x)
    except Exception:
        return math.nan


def parse_iso(x: Optional[str]) -> Optional[str]:
    """
    Parsea una fecha ISO y la normaliza

    Args:
        x: String con fecha ISO

    Returns:
        Fecha normalizada en formato ISO o None
    """
    if not x:
        return None
    try:
        return dtp.parse(x).isoformat()
    except Exception:
        return None


def compute_er(
    play: Any,
    like: Any,
    share: Any,
    comment: Any,
    collect: Any
) -> float:
    """
    Calcula el Engagement Rate basado en reproducciones
    ER = (likes + shares + comments + collects) / plays

    Args:
        play: Número de reproducciones
        like: Número de likes
        share: Número de shares
        comment: Número de comentarios
        collect: Número de guardados

    Returns:
        Engagement Rate o NaN si no se puede calcular
    """
    plays = to_float(play)
    parts = [
        to_float(like),
        to_float(share),
        to_float(comment),
        to_float(collect)
    ]
    eng = sum(p for p in parts if not math.isnan(p))

    if plays and plays > 0:
        return eng / plays
    return math.nan


def compute_total_engagement(
    like: Any,
    share: Any,
    comment: Any,
    collect: Any
) -> float:
    """
    Calcula el engagement total (suma de todas las interacciones)

    Returns:
        Suma total de interacciones
    """
    parts = [
        to_float(like),
        to_float(share),
        to_float(comment),
        to_float(collect)
    ]
    return sum(p for p in parts if not math.isnan(p))


def normalize_item(it: Dict[str, Any], item_id: str) -> Dict[str, Any]:
    """
    Normaliza un item de TikTok a un formato estandarizado
    Extrae campos, calcula métricas y añade features

    Args:
        it: Item raw de Apify
        item_id: ID único del item

    Returns:
        Diccionario normalizado con todos los campos procesados
    """
    text = it.get("text") or ""

    # Extraer métricas base
    play_count = to_float(dotted_get(it, "playCount"))
    digg_count = to_float(dotted_get(it, "diggCount"))
    share_count = to_float(dotted_get(it, "shareCount"))
    comment_count = to_float(dotted_get(it, "commentCount"))
    collect_count = to_float(dotted_get(it, "collectCount"))

    # Calcular engagement
    er_play = compute_er(
        play_count,
        digg_count,
        share_count,
        comment_count,
        collect_count
    )
    total_engagement = compute_total_engagement(
        digg_count,
        share_count,
        comment_count,
        collect_count
    )

    # Extraer features del texto
    hashtags = extract_hashtags(text)
    mentions = extract_mentions(text)

    # Construir row normalizado
    row = {
        # Identificadores
        "id": item_id,
        "webVideoUrl": dotted_get(it, "webVideoUrl"),

        # Metadatos temporales
        "createTimeISO": parse_iso(dotted_get(it, "createTimeISO")),

        # Contenido
        "text": text,
        "text_len": len(text),

        # Autor
        "author_name": dotted_get(it, "authorMeta.name"),
        "author_id": dotted_get(it, "authorMeta.id"),
        "avatar_url": dotted_get(it, "authorMeta.avatar"),
        "author_verified": bool(dotted_get(it, "authorMeta.verified", False)),

        # Video metadata
        "cover_url": (
            dotted_get(it, "videoMeta.cover")
            or dotted_get(it, "videoMeta.coverUrl")
        ),
        "duration_s": to_float(dotted_get(it, "videoMeta.duration")),
        "video_url": dotted_get(it, "videoUrl"),

        # Música
        "music_name": dotted_get(it, "musicMeta.musicName"),
        "music_author": dotted_get(it, "musicMeta.musicAuthor"),
        "music_original": bool(
            dotted_get(it, "musicMeta.musicOriginal", False)
        ),

        # Métricas de engagement
        "playCount": play_count,
        "diggCount": digg_count,
        "shareCount": share_count,
        "commentCount": comment_count,
        "collectCount": collect_count,

        # Métricas calculadas
        "ER_play": er_play,
        "total_engagement": total_engagement,

        # Features extraídas
        "n_hashtags": len(hashtags),
        "hashtags": hashtags,
        "n_mentions": len(mentions),
        "mentions": mentions,

        # Features adicionales
        "has_music": bool(dotted_get(it, "musicMeta.musicName")),
        "is_original_music": bool(
            dotted_get(it, "musicMeta.musicOriginal", False)
        ),
    }

    return row


def filter_valid_items(
    items: list[Dict[str, Any]]
) -> list[Dict[str, Any]]:
    """
    Filtra items válidos (que tengan URL de video)

    Args:
        items: Lista de items a filtrar

    Returns:
        Lista de items válidos
    """
    return [
        item for item in items
        if dotted_get(item, "webVideoUrl")
    ]
