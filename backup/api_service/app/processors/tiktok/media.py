"""
Módulo para descarga concurrente de imágenes desde URLs
Incluye manejo de reintentos y tolerancia a fallos
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import requests
from PIL import Image
from tqdm import tqdm


def _get_with_retries(
    url: str,
    timeout: int = 25,
    tries: int = 4,
    backoff: float = 0.8
) -> Optional[requests.Response]:
    """
    Realiza una petición HTTP con reintentos exponenciales

    Args:
        url: URL a descargar
        timeout: Timeout en segundos
        tries: Número máximo de intentos
        backoff: Factor de espera exponencial

    Returns:
        Response de requests o None si falla
    """
    for i in range(tries):
        try:
            r = requests.get(url, timeout=timeout, stream=True)
            if r.status_code == 200:
                return r
        except Exception:
            pass
        # Espera exponencial entre reintentos
        time.sleep(backoff * (2 ** i))
    return None


def download_image(url: Optional[str], dest: Path) -> Optional[str]:
    """
    Descarga una imagen desde una URL y la guarda como JPEG

    Args:
        url: URL de la imagen
        dest: Path destino donde guardar

    Returns:
        String con el path si tuvo éxito, None si falló
    """
    if not url:
        return None

    r = _get_with_retries(url)
    if not r:
        return None

    try:
        # Abrir imagen y convertir a RGB
        img = Image.open(BytesIO(r.content)).convert("RGB")

        # Crear directorio si no existe
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Guardar como JPEG con calidad 90
        img.save(dest, "JPEG", quality=90)

        return str(dest)
    except Exception:
        return None


def bulk_download(
    rows: List[Dict[str, Any]],
    img_dir: Path,
    max_workers: int = 16
) -> List[Dict[str, Any]]:
    """
    Descarga imágenes en paralelo para una lista de rows
    Descarga avatar y cover de cada item

    Args:
        rows: Lista de diccionarios con datos normalizados
        img_dir: Directorio donde guardar las imágenes
        max_workers: Número de workers para descarga paralela

    Returns:
        Lista de rows actualizada con paths de imágenes
    """
    # Crear lista de trabajos (row_idx, url, dest, target_key)
    jobs: List[Tuple[int, str, Path, str]] = []

    for i, r in enumerate(rows):
        # Avatar del autor
        if r.get("avatar_url"):
            jobs.append((
                i,
                r["avatar_url"],
                img_dir / f"{r['id']}_avatar.jpg",
                "avatar_path"
            ))

        # Cover del video
        if r.get("cover_url"):
            jobs.append((
                i,
                r["cover_url"],
                img_dir / f"{r['id']}_cover.jpg",
                "cover_path"
            ))

    # Ejecutar descargas en paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        # Mapear futures a sus metadatos
        futmap = {
            ex.submit(download_image, url, dest): (i, target_key, dest)
            for (i, url, dest, target_key) in jobs
        }

        # Procesar resultados con barra de progreso
        with tqdm(
            total=len(futmap),
            desc="Descargando imágenes",
            unit="img"
        ) as pbar:
            for fut in as_completed(futmap):
                i, key, dest = futmap[fut]
                try:
                    path = fut.result()
                except Exception:
                    path = None

                # Actualizar row con path de imagen
                rows[i][key] = path
                pbar.update(1)

    return rows


def download_sample_images(
    rows: List[Dict[str, Any]],
    img_dir: Path,
    sample_size: int = 100,
    max_workers: int = 16
) -> List[Dict[str, Any]]:
    """
    Descarga imágenes solo de una muestra de items
    Útil para testing o previews

    Args:
        rows: Lista completa de items
        img_dir: Directorio destino
        sample_size: Número de items a descargar
        max_workers: Workers para descarga paralela

    Returns:
        Lista de rows con paths actualizados
    """
    import random

    # Crear copia para no modificar original
    rows_copy = rows.copy()

    # Seleccionar muestra aleatoria
    sample_indices = random.sample(
        range(len(rows_copy)),
        min(sample_size, len(rows_copy))
    )

    # Descargar solo la muestra
    for idx in sample_indices:
        row = rows_copy[idx]

        # Avatar
        if row.get("avatar_url"):
            dest = img_dir / f"{row['id']}_avatar.jpg"
            path = download_image(row["avatar_url"], dest)
            row["avatar_path"] = path

        # Cover
        if row.get("cover_url"):
            dest = img_dir / f"{row['id']}_cover.jpg"
            path = download_image(row["cover_url"], dest)
            row["cover_path"] = path

    return rows_copy
