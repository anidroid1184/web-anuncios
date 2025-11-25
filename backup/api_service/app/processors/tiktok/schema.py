"""
Esquemas y funciones de utilidad para validar y manipular items de TikTok
"""
from __future__ import annotations
from typing import Any, Dict, Optional


def dotted_get(
    obj: Dict[str, Any],
    dotted_key: str,
    default=None
) -> Any:
    """
    Obtiene un valor de un diccionario usando notación de puntos
    Soporta tanto claves flatten ("authorMeta.name") como anidadas

    Args:
        obj: Diccionario fuente
        dotted_key: Clave con puntos (ej: "authorMeta.name")
        default: Valor por defecto si no se encuentra

    Returns:
        Valor encontrado o default

    Example:
        >>> data = {"authorMeta.name": "john"}
        >>> dotted_get(data, "authorMeta.name")
        'john'
        >>> data = {"authorMeta": {"name": "john"}}
        >>> dotted_get(data, "authorMeta.name")
        'john'
    """
    # Primero intentar con la clave directa (JSON flatten)
    if dotted_key in obj:
        return obj.get(dotted_key, default)

    # Si no existe, navegar por la estructura anidada
    cur = obj
    for part in dotted_key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def infer_item_id(item: Dict[str, Any], fallback: str) -> str:
    """
    Infiere el ID de un item desde su URL de video

    Args:
        item: Item de TikTok
        fallback: ID alternativo si no se puede inferir

    Returns:
        ID del video o fallback

    Example:
        >>> item = {"webVideoUrl": "https://www.tiktok.com/@user/video/123456"}
        >>> infer_item_id(item, "unknown")
        '123456'
    """
    url = dotted_get(item, "webVideoUrl")
    if isinstance(url, str) and "/video/" in url:
        return url.split("/video/")[-1]
    return fallback


def is_valid_tiktok_item(item: Dict[str, Any]) -> bool:
    """
    Valida que un item tenga los campos mínimos requeridos

    Args:
        item: Item a validar

    Returns:
        True si el item es válido
    """
    required_fields = ["webVideoUrl"]
    return all(dotted_get(item, field) for field in required_fields)


def extract_hashtags(text: Optional[str]) -> list[str]:
    """
    Extrae los hashtags de un texto

    Args:
        text: Texto del que extraer hashtags

    Returns:
        Lista de hashtags sin el símbolo #

    Example:
        >>> extract_hashtags("Hola #fyp #viral")
        ['fyp', 'viral']
    """
    if not text:
        return []

    import re
    return re.findall(r'#(\w+)', text)


def extract_mentions(text: Optional[str]) -> list[str]:
    """
    Extrae las menciones (@) de un texto

    Args:
        text: Texto del que extraer menciones

    Returns:
        Lista de usuarios mencionados sin @

    Example:
        >>> extract_mentions("Hola @user1 y @user2")
        ['user1', 'user2']
    """
    if not text:
        return []

    import re
    return re.findall(r'@(\w+)', text)
