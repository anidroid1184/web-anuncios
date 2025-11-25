"""
Facebook Routes - Endpoints para el scraper de Facebook Ads Library
Usa FacebookActor para encapsular toda la lógica de interacción
"""

from .facebook_actor import FacebookActor
from app.processors.facebook.download_images_from_csv import (
    make_session,
    extract_urls_from_snapshot,
    iter_csv_snapshot_rows,
    download_one,
)
from app.processors.facebook.analyze_dataset import analyze, analyze_jsonl
from app.processors.facebook.extract_dataset import fetch_and_store_run_dataset
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
import os
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, root_validator, AnyUrl
import asyncio
from pathlib import Path

# Ruta al root del repo (para resolver rutas relativas desde api_service)
repo_root = Path(__file__).resolve().parents[6]
# Ruta al api_service (carpeta donde se ejecuta la app)
api_root = Path(__file__).resolve().parents[5]


def get_facebook_saved_base() -> Path:
    """Resuelve la carpeta base donde están los datasets guardados de Facebook.
    NUEVA UBICACIÓN: storage/facebook/
    """
    candidates = [
        # Nueva estructura: storage/facebook
        api_root / 'storage' / 'facebook',
        # Compatibilidad con estructura antigua
        api_root / 'datasets' / 'datasets' / 'saved_datasets' / 'facebook',
        api_root / 'datasets' / 'saved_datasets' / 'facebook',
        repo_root / 'api_service' / 'storage' / 'facebook',
        repo_root / 'api_service' / 'datasets' /
        'datasets' / 'saved_datasets' / 'facebook',
        repo_root / 'api_service' / 'datasets' / 'saved_datasets' / 'facebook',
    ]
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    return candidates[0]


# importar el extractor creado

# Drive service (opcional)
try:
    from app.services.drive_service import DriveService
    from pathlib import Path

    # Construir lista de candidatos para las credenciales, priorizando variables de entorno
    repo_root = Path(__file__).resolve().parents[6]
    api_root = Path(__file__).resolve().parents[5]

    candidates = []
    # 1) variables de entorno (dos nombres soportados)
    if os.getenv('GOOGLE_CREDENTIALS_PATH'):
        candidates.append(Path(os.getenv('GOOGLE_CREDENTIALS_PATH')))
    if os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH'):
        candidates.append(Path(os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH')))
    # soporte estándar de Google SDK
    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        candidates.append(Path(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))

    # 2) ruta dentro de api_service/credentials
    candidates.append(api_root / 'credentials' / 'credsDrive.json')

    # 3) ruta compartida en repo root: shared/credentials/credsDrive.json
    candidates.append(repo_root / 'shared' / 'credentials' / 'credsDrive.json')
    candidates.append(repo_root / 'shared' /
                      'credentials' / 'credentials.json')

    # Elegir el primer candidato existente
    credentials_path = None
    for c in candidates:
        try:
            if c and c.exists():
                credentials_path = str(c)
                break
        except Exception:
            continue

    if credentials_path is None:
        # fallback: usar valor de ENV si está pero puede no existir en disco
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH') or os.getenv(
            'GOOGLE_DRIVE_CREDENTIALS_PATH')

    # Guardar para diagnóstico (puede ser None)
    drive_credentials_path = credentials_path

    try:
        if not credentials_path:
            raise FileNotFoundError(
                'No credentials path found for DriveService')
        drive_service = DriveService(credentials_path)
    except Exception as _e:
        drive_service = None
        print(
            f"WARNING: DriveService not initialized (credentials_path={credentials_path}): {_e}")
except Exception:
    drive_service = None

# GCS service (Google Cloud Storage)
try:
    from app.services.gcs_service import GCSService

    # Usar el mismo credentials_path o variables de entorno
    gcs_credentials_path = credentials_path or os.getenv(
        'GOOGLE_APPLICATION_CREDENTIALS')

    try:
        # Intentar inicializar GCS
        gcs_service = GCSService(
            credentials_path=gcs_credentials_path,
            bucket_name=os.getenv('GOOGLE_BUCKET_NAME', 'proveedor-1')
        )
    except Exception as _e:
        gcs_service = None
        print(
            f"WARNING: GCSService not initialized (credentials_path={gcs_credentials_path}): {_e}")
except Exception:
    gcs_service = None

# Facebook Actor initialization
actor_facebook = None
try:
    actor_facebook = FacebookActor()
except Exception as _e:
    print(f"WARNING: FacebookActor not initialized: {_e}")

router = APIRouter(tags=["Facebook"])

# Track which credentials path was used (for diagnostics)
drive_credentials_path: str | None = None


@router.get('/debug/drive_status')
async def debug_drive_status():
    """Endpoint de diagnóstico: devuelve si DriveService y GCSService están inicializados."""
    return {
        'drive_service_configured': bool(drive_service),
        'gcs_service_configured': bool(gcs_service),
        'credentials_path': drive_credentials_path,
        'bucket_name': os.getenv('GOOGLE_BUCKET_NAME', 'proveedor-1') if gcs_service else None
    }


@router.post("/scrape_and_save", status_code=200)
async def scrape_and_save(request: 'SimpleScrapeRequest'):
    """
    Inicia el scraper con una única URL, espera al resultado y guarda
    el dataset en `datasets/facebook/<run_id>/`. Además intenta generar
    automáticamente el manifest 'prepared' (preparación de top N) y devuelve
    la ruta local del JSON generado para que posteriores llamadas puedan
    usar solo el `run_id`.
    """
    try:
        actor = FacebookActor()

        # construir input mínimo para el actor
        actor_input = {
            "count": int(request.count or 100),
            "scrapeAdDetails": True,
            "urls": [{"url": str(request.url)}],
        }

        # iniciar actor asíncrono
        run_data = await asyncio.to_thread(actor.run_async, actor_input)

        if not run_data or not run_data.get("id"):
            raise HTTPException(
                status_code=500,
                detail=("No se pudo iniciar el actor"),
            )

        run_id = run_data.get("id")
        run_id_str = str(run_id)

        # esperar hasta SUCCEEDED o timeout
        timeout = int(request.timeout or 600)
        poll_interval = 5
        elapsed = 0
        while elapsed < timeout:
            status_data = await asyncio.to_thread(actor.get_run_status, run_id_str)
            status = status_data.get("status") if status_data else None
            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "ABORTED"):
                raise HTTPException(status_code=500, detail=(
                    f"Run finalizó con estado {status}"),)
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        if elapsed >= timeout:
            raise HTTPException(status_code=504, detail=(
                "Timeout esperando al run de Apify"),)

        # una vez SUCCEEDED, descargar dataset y guardarlo
        if not run_id_str:
            raise HTTPException(status_code=500, detail="Run id inválido")

        # Guardar dataset en disco
        meta = fetch_and_store_run_dataset(run_id_str)

        # Intentar localizar el CSV/JSONL generado
        import pathlib
        import json

        run_dir = pathlib.Path(str(meta.get("saved_jsonl", ""))).parent
        csv_path = run_dir / f"{run_id_str}.csv"

        # Construir stats (reutiliza analyze si hay CSV)
        stats = {}
        if csv_path.exists():
            stats = analyze(csv_path)
        else:
            jsonl_path = run_dir / f"{run_id_str}.jsonl"
            if jsonl_path.exists():
                stats = {}
                with jsonl_path.open("r", encoding="utf-8") as jf:
                    for line in jf:
                        try:
                            item = json.loads(line)
                        except Exception:
                            continue
                        ad_id = item.get("ad_archive_id") or item.get(
                            "adArchiveID") or item.get("id") or "unknown"
                        snap = item.get("snapshot") or {}
                        urls = extract_urls_from_snapshot(
                            snap) if isinstance(snap, dict) else []
                        ent = stats.setdefault(
                            ad_id, {"ad_id": ad_id, "urls": [], "images": 0, "videos": 0, "score": 0})
                        ent["urls"].extend(urls)
                        ent["images"] = len(snap.get("images") or []) if isinstance(
                            snap, dict) else 0
                        ent["videos"] = len(snap.get("videos") or []) if isinstance(
                            snap, dict) else 0
                        ent["total_media"] = ent["images"] + ent["videos"]
                        ent["score"] = float(ent["total_media"]) if ent.get(
                            "total_media") is not None else 0

        items = sorted(stats.values(), key=lambda x: x.get(
            "score", 0), reverse=True)
        top_n = 10
        top_ads = [it.get("ad_id") for it in items[:top_n]]

        # Descargar medios de los top N
        media_dir = run_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        session = make_session()
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = []
            if csv_path.exists():
                for row, snapshot in iter_csv_snapshot_rows(csv_path):
                    ad_id = row.get("ad_archive_id") or row.get(
                        "ad_id") or "unknown"
                    if ad_id not in top_ads:
                        continue
                    if not snapshot:
                        continue
                    urls = extract_urls_from_snapshot(snapshot)
                    for u in urls:
                        futures.append(
                            ex.submit(download_one, session, u, media_dir, prefix=ad_id))
            else:
                jsonl_path = run_dir / f"{run_id_str}.jsonl"
                if jsonl_path.exists():
                    with jsonl_path.open("r", encoding="utf-8") as jf:
                        for line in jf:
                            try:
                                item = json.loads(line)
                            except Exception:
                                continue
                            ad_id = item.get("ad_archive_id") or item.get(
                                "adArchiveID") or item.get("id") or "unknown"
                            if ad_id not in top_ads:
                                continue
                            snap = item.get("snapshot") or {}
                            if not isinstance(snap, dict):
                                continue
                            urls = extract_urls_from_snapshot(snap)
                            for u in urls:
                                futures.append(
                                    ex.submit(download_one, session, u, media_dir, prefix=ad_id))

            downloaded = 0
            failures = 0
            for fut in as_completed(futures):
                url, path = fut.result()
                if path:
                    downloaded += 1
                else:
                    failures += 1

        # Intentar generar el manifest 'prepared' automáticamente llamando al preparer
        prepared_json = None
        try:
            preparer_result = await preparer_run(
                run_id=run_id_str,
                top=10,
                method='heuristic',
                max_dim=512,
                jpeg_quality=70,
                limit_per_ad=5,
                drive_folder_id=None,
            )
            if isinstance(preparer_result, dict):
                prepared_json = preparer_result.get('prepared_json')
        except Exception:
            prepared_json = None

        return {
            "status": "ok",
            "run_id": run_id_str,
            "dataset_meta": meta,
            "top_ads": top_ads,
            "downloaded_media_count": downloaded,
            "download_failures": failures,
            "media_dir": str(media_dir),
            "prepared_json": prepared_json,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/debug/get_public_urls', tags=["bucket-cloud-console"])
async def get_public_urls(
    run_id: Optional[str] = None,
    prefix: Optional[str] = None,
    blob_path: Optional[str] = None
):
    """
    Obtiene las URLs públicas de los archivos en el bucket de GCS.

    Casos de uso:
    1. Listar todos los archivos de un run: ?run_id=R4aPb92jhy3hhQxhN
    2. Listar archivos con un prefijo: ?prefix=test/
    3. Obtener URL de un archivo específico: ?blob_path=test/test.txt

    Args:
        run_id: ID del run para listar archivos en runs/{run_id}/prepared/
        prefix: Prefijo personalizado para filtrar archivos
        blob_path: Ruta específica de un blob para obtener su URL

    Returns:
        Lista de archivos con sus URLs públicas y metadata
    """
    try:
        if gcs_service is None:
            raise HTTPException(
                status_code=503,
                detail='GCS service not configured. Set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_BUCKET_NAME'
            )

        bucket_name = gcs_service.default_bucket_name

        # Caso 1: Obtener URL de un archivo específico
        if blob_path:
            try:
                # Verificar si el blob existe
                if not gcs_service.blob_exists(blob_path):
                    return {
                        'status': 'error',
                        'message': f'Blob not found: {blob_path}',
                        'blob_path': blob_path,
                        'bucket': bucket_name
                    }

                # Obtener información del blob
                bucket = gcs_service.get_bucket()
                blob = bucket.blob(blob_path)
                blob.reload()  # Cargar metadata

                return {
                    'status': 'success',
                    'blob_path': blob_path,
                    'bucket': bucket_name,
                    'public_url': blob.public_url,
                    'media_link': blob.media_link,
                    'size': blob.size,
                    'content_type': blob.content_type,
                    'updated': blob.updated.isoformat() if blob.updated else None,
                    'console_url': f'https://console.cloud.google.com/storage/browser/_details/{bucket_name}/{blob_path}',
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f'Error getting blob info: {str(e)}'
                )

        # Caso 2: Listar archivos con prefijo
        search_prefix = None
        if run_id:
            search_prefix = f'runs/{run_id}/prepared/'
        elif prefix:
            search_prefix = prefix

        try:
            blobs = gcs_service.list_blobs(prefix=search_prefix)

            if not blobs:
                return {
                    'status': 'success',
                    'message': 'No files found',
                    'bucket': bucket_name,
                    'prefix': search_prefix or 'all',
                    'files': [],
                    'count': 0
                }

            files = []
            for blob_info in blobs:
                files.append({
                    'name': blob_info['name'],
                    'public_url': blob_info['public_url'],
                    'size': blob_info['size'],
                    'content_type': blob_info['content_type'],
                    'updated': blob_info['updated'].isoformat() if blob_info['updated'] else None,
                })

            return {
                'status': 'success',
                'bucket': bucket_name,
                'prefix': search_prefix or 'all',
                'files': files,
                'count': len(files),
                'console_url': f'https://console.cloud.google.com/storage/browser/{bucket_name}/{search_prefix or ""}',
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f'Error listing blobs: {str(e)}'
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/runs/{run_id}/gcs_files', tags=["bucket-cloud-console"])
async def get_run_gcs_files(
    run_id: str,
    generate_signed_urls: bool = False,
    expiration_hours: int = 1
):
    """
    Obtiene todos los archivos de un run específico en GCS con URLs públicas o firmadas.

    Args:
        run_id: ID del run
        generate_signed_urls: Si es True, genera URLs firmadas temporales en lugar de URLs públicas
        expiration_hours: Horas de validez para URLs firmadas (por defecto 1 hora)

    Returns:
        Archivos organizados por tipo (manifest, media) con sus URLs
    """
    try:
        if gcs_service is None:
            raise HTTPException(
                status_code=503,
                detail='GCS service not configured'
            )

        prefix = f'runs/{run_id}/prepared/'
        bucket_name = gcs_service.default_bucket_name

        try:
            blobs = gcs_service.list_blobs(prefix=prefix)

            if not blobs:
                return {
                    'status': 'success',
                    'run_id': run_id,
                    'message': 'No files found for this run in GCS',
                    'bucket': bucket_name,
                    'prefix': prefix,
                    'manifest': None,
                    'media_by_ad': {},
                    'total_files': 0
                }

            manifest_file = None
            media_by_ad = {}

            for blob_info in blobs:
                blob_name = blob_info['name']

                # Generar URL firmada si se solicita
                if generate_signed_urls:
                    try:
                        url = gcs_service.get_signed_url(
                            blob_name=blob_name,
                            expiration=expiration_hours * 3600
                        )
                    except Exception:
                        url = blob_info['public_url']
                else:
                    url = blob_info['public_url']

                file_info = {
                    'blob_name': blob_name,
                    'url': url,
                    'url_type': 'signed' if generate_signed_urls else 'public',
                    'size': blob_info['size'],
                    'content_type': blob_info['content_type'],
                    'updated': blob_info['updated'].isoformat() if blob_info['updated'] else None,
                }

                # Clasificar archivo
                if 'manifest.json' in blob_name or blob_name.endswith('.json'):
                    manifest_file = file_info
                else:
                    # Extraer ad_id del path: runs/{run_id}/prepared/{ad_id}/{filename}
                    parts = blob_name.split('/')
                    if len(parts) >= 4:
                        ad_id = parts[3]
                        if ad_id not in media_by_ad:
                            media_by_ad[ad_id] = []
                        media_by_ad[ad_id].append(file_info)

            total_files = len(blobs)

            return {
                'status': 'success',
                'run_id': run_id,
                'bucket': bucket_name,
                'prefix': prefix,
                'manifest': manifest_file,
                'media_by_ad': media_by_ad,
                'total_files': total_files,
                'ads_count': len(media_by_ad),
                'url_expiration_hours': expiration_hours if generate_signed_urls else None,
                'console_url': f'https://console.cloud.google.com/storage/browser/{bucket_name}/{prefix}',
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f'Error listing files: {str(e)}'
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/debug/get_test_file', tags=["bucket-cloud-console"])
async def get_test_file(
    blob_path: str = "test/test.txt",
    expiration_hours: int = 24
):
    """
    Obtiene el contenido y las URLs del archivo test.txt (o cualquier archivo de texto).

    Args:
        blob_path: Ruta del archivo en el bucket (por defecto: test/test.txt)
        expiration_hours: Horas de validez para la URL firmada (por defecto: 24 horas, máximo: 168 = 7 días)

    Returns:
        Contenido del archivo, URLs públicas y firmadas
    """
    try:
        if gcs_service is None:
            raise HTTPException(
                status_code=503,
                detail='GCS service not configured. Set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_BUCKET_NAME'
            )

        # Validar expiration_hours
        if expiration_hours < 1:
            expiration_hours = 1
        elif expiration_hours > 168:  # Máximo 7 días
            expiration_hours = 168

        bucket_name = gcs_service.default_bucket_name

        # Verificar si el archivo existe
        if not gcs_service.blob_exists(blob_path):
            return {
                'status': 'error',
                'message': f'File not found: {blob_path}',
                'bucket': bucket_name,
                'blob_path': blob_path,
                'suggestion': 'Upload a test file first using POST /debug/upload_test_file'
            }

        # Obtener información del blob
        bucket = gcs_service.get_bucket()
        blob = bucket.blob(blob_path)
        blob.reload()

        # Descargar contenido si es texto
        content = None
        try:
            if blob.content_type and 'text' in blob.content_type:
                content_bytes = blob.download_as_bytes()
                content = content_bytes.decode('utf-8')
        except Exception as e:
            content = f"Error reading content: {str(e)}"

        # Generar URL firmada
        signed_url = None
        import datetime
        expiration_seconds = expiration_hours * 3600
        expires_at = datetime.datetime.now(
            datetime.timezone.utc) + datetime.timedelta(hours=expiration_hours)

        try:
            signed_url = gcs_service.get_signed_url(
                blob_name=blob_path,
                expiration=expiration_seconds
            )
        except Exception as e:
            signed_url = f"Error generating signed URL: {str(e)}"

        return {
            'status': 'success',
            'blob_path': blob_path,
            'bucket': bucket_name,
            'file_info': {
                'size': blob.size,
                'content_type': blob.content_type,
                'updated': blob.updated.isoformat() if blob.updated else None,
                'created': blob.time_created.isoformat() if blob.time_created else None,
            },
            'content': content,
            'urls': {
                'public_url': blob.public_url,
                'media_link': blob.media_link,
                'signed_url': signed_url,
                'signed_url_expires_in': f'{expiration_hours} hours' if isinstance(signed_url, str) and signed_url.startswith('http') else None,
                'signed_url_expires_at': expires_at.isoformat() if isinstance(signed_url, str) and signed_url.startswith('http') else None
            },
            'console_url': f'https://console.cloud.google.com/storage/browser/_details/{bucket_name}/{blob_path}',
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/runs/list', tags=["Facebook"])
async def list_saved_runs():
    """
    Lista todos los runs guardados localmente con información de tamaño.

    Returns:
        Lista de runs con metadata: run_id, tamaño, archivos, fecha de creación
    """
    try:
        from pathlib import Path
        import os
        from datetime import datetime

        base = get_facebook_saved_base()

        if not base.exists():
            return {
                'status': 'success',
                'runs': [],
                'total_runs': 0,
                'total_size_mb': 0
            }

        runs = []
        total_size = 0

        for run_dir in base.iterdir():
            if not run_dir.is_dir():
                continue

            run_id = run_dir.name

            # Calcular tamaño
            size_bytes = sum(
                f.stat().st_size for f in run_dir.rglob('*') if f.is_file()
            )
            size_mb = size_bytes / (1024 * 1024)
            total_size += size_mb

            # Contar archivos
            file_count = sum(1 for f in run_dir.rglob('*') if f.is_file())

            # Fecha de creación
            created = datetime.fromtimestamp(run_dir.stat().st_ctime)

            # Verificar qué archivos tiene
            has_csv = (run_dir / f'{run_id}.csv').exists()
            has_jsonl = (run_dir / f'{run_id}.jsonl').exists()
            has_media = (run_dir / 'media').exists()
            has_prepared = (run_dir / 'prepared').exists()

            media_count = 0
            if has_media:
                media_count = sum(1 for f in (
                    run_dir / 'media').iterdir() if f.is_file())

            runs.append({
                'run_id': run_id,
                'size_mb': round(size_mb, 2),
                'size_bytes': size_bytes,
                'file_count': file_count,
                'created': created.isoformat(),
                'has_csv': has_csv,
                'has_jsonl': has_jsonl,
                'has_media': has_media,
                'media_count': media_count,
                'has_prepared': has_prepared,
                'path': str(run_dir)
            })

        # Ordenar por tamaño (mayor a menor)
        runs.sort(key=lambda x: x['size_mb'], reverse=True)

        return {
            'status': 'success',
            'runs': runs,
            'total_runs': len(runs),
            'total_size_mb': round(total_size, 2),
            'base_path': str(base)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/runs/{run_id}', tags=["Facebook"])
async def delete_run(run_id: str):
    """
    Elimina un run específico del almacenamiento local.

    Args:
        run_id: ID del run a eliminar

    Returns:
        Información sobre la eliminación: espacio liberado, archivos eliminados
    """
    try:
        import shutil
        from pathlib import Path

        base = get_facebook_saved_base()
        run_dir = base / run_id

        if not run_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f'Run {run_id} not found'
            )

        # Calcular tamaño antes de eliminar
        size_bytes = sum(
            f.stat().st_size for f in run_dir.rglob('*') if f.is_file()
        )
        size_mb = size_bytes / (1024 * 1024)

        file_count = sum(1 for f in run_dir.rglob('*') if f.is_file())

        # Eliminar directorio completo
        shutil.rmtree(run_dir)

        return {
            'status': 'success',
            'message': f'Run {run_id} deleted successfully',
            'run_id': run_id,
            'freed_space_mb': round(size_mb, 2),
            'files_deleted': file_count
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/runs/cleanup', tags=["Facebook"])
async def cleanup_runs(
    keep_latest: int = 1,
    min_size_mb: Optional[float] = None,
    older_than_days: Optional[int] = None
):
    """
    Limpia datasets antiguos según criterios.

    Args:
        keep_latest: Mantener los N runs más recientes (default: 1)
        min_size_mb: Solo eliminar runs mayores a este tamaño en MB
        older_than_days: Solo eliminar runs más antiguos que N días

    Returns:
        Lista de runs eliminados y espacio liberado
    """
    try:
        from pathlib import Path
        from datetime import datetime, timedelta
        import shutil

        base = get_facebook_saved_base()

        if not base.exists():
            return {
                'status': 'success',
                'message': 'No runs found',
                'deleted_runs': [],
                'total_freed_mb': 0
            }

        # Obtener todos los runs
        all_runs = []
        for run_dir in base.iterdir():
            if not run_dir.is_dir():
                continue

            run_id = run_dir.name
            size_bytes = sum(
                f.stat().st_size for f in run_dir.rglob('*') if f.is_file())
            size_mb = size_bytes / (1024 * 1024)
            created = datetime.fromtimestamp(run_dir.stat().st_ctime)

            all_runs.append({
                'run_id': run_id,
                'path': run_dir,
                'size_mb': size_mb,
                'size_bytes': size_bytes,
                'created': created
            })

        # Ordenar por fecha (más reciente primero)
        all_runs.sort(key=lambda x: x['created'], reverse=True)

        # Determinar cuáles eliminar
        to_delete = []

        for i, run in enumerate(all_runs):
            # Mantener los N más recientes
            if i < keep_latest:
                continue

            # Filtrar por tamaño mínimo
            if min_size_mb and run['size_mb'] < min_size_mb:
                continue

            # Filtrar por antigüedad
            if older_than_days:
                age_days = (datetime.now() - run['created']).days
                if age_days < older_than_days:
                    continue

            to_delete.append(run)

        # Eliminar runs seleccionados
        deleted = []
        total_freed = 0

        for run in to_delete:
            try:
                file_count = sum(
                    1 for f in run['path'].rglob('*') if f.is_file())
                shutil.rmtree(run['path'])

                deleted.append({
                    'run_id': run['run_id'],
                    'freed_mb': round(run['size_mb'], 2),
                    'files_deleted': file_count,
                    'created': run['created'].isoformat()
                })
                total_freed += run['size_mb']
            except Exception as e:
                deleted.append({
                    'run_id': run['run_id'],
                    'error': str(e)
                })

        return {
            'status': 'success',
            'message': f'Deleted {len(deleted)} runs, freed {round(total_freed, 2)} MB',
            'deleted_runs': deleted,
            'kept_runs': len(all_runs) - len(deleted),
            'total_freed_mb': round(total_freed, 2),
            'criteria': {
                'keep_latest': keep_latest,
                'min_size_mb': min_size_mb,
                'older_than_days': older_than_days
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# MODELOS PYDANTIC
# ==========================================

class UrlItem(BaseModel):
    url: AnyUrl = Field(
        ...,
        description="URL de búsqueda de Facebook/Meta",
    )


class ScrapePageAds(BaseModel):
    activeStatus: Optional[str] = Field(default="all")
    countryCode: Optional[str] = Field(default="ALL")


class FacebookScraperInput(BaseModel):
    """
    Input esperado por el actor (formato cerrado):
    {
      "count": 100,
      "scrapeAdDetails": true,
      "scrapePageAds.activeStatus": "all",
      "scrapePageAds.countryCode": "ALL",
      "urls": [{"url": "https://..."}]
    }
    """
    count: int = Field(default=100, ge=1)
    scrapeAdDetails: bool = Field(default=True)
    scrapePageAds: Optional[ScrapePageAds] = Field(
        default_factory=ScrapePageAds,
    )
    urls: List[UrlItem] = Field(...)

    @root_validator(pre=False, skip_on_failure=True)
    def ensure_urls_present(cls, values):
        urls = values.get("urls")
        if not urls or len(urls) == 0:
            raise ValueError("'urls' debe tener al menos 1 elemento")
        return values


class FacebookStartResponse(BaseModel):
    """Respuesta al iniciar el scraper"""
    status: str
    run_id: str
    message: str


class FacebookResponse(BaseModel):
    """Respuesta del scraper de Facebook"""
    status: str
    run_id: Optional[str] = None
    actor_status: Optional[str] = None
    count: int
    data: List[Dict]
    message: Optional[str] = None


# ==========================================
# ENDPOINTS
# ==========================================

@router.post(
    "/scrape",
    response_model=FacebookStartResponse,
    status_code=202
)
async def scrape_facebook_ads(request: FacebookScraperInput):
    """
    Inicia el scraper de Facebook Ads Library de forma asíncrona

    El proceso de scraping se ejecuta en segundo plano en Apify.
    Retorna inmediatamente un run_id que se usa para consultar
    el estado y los resultados posteriormente.

    Flujo recomendado:
    1. POST /scrape -> Recibe run_id (202 ACCEPTED)
    2. GET /runs/{run_id} -> Consultar estado
    3. GET /runs/{run_id}/results -> Obtener anuncios cuando SUCCEEDED

    Args:
        request: Parámetros de búsqueda según el actor de Apify

    Returns:
        202 ACCEPTED: FacebookStartResponse con run_id para monitoreo
    """
    try:
        actor = FacebookActor()

        # Construir input del actor
        actor_input = actor.build_actor_input(request)

        # Iniciar actor asíncrono
        run_data = actor.run_async(actor_input=actor_input)

        if not run_data or not run_data.get("id"):
            raise HTTPException(
                status_code=500,
                detail="No se pudo iniciar el actor de Facebook"
            )

        run_id = run_data.get("id", "")

        return FacebookStartResponse(
            status="started",
            run_id=run_id,
            message=(
                f"Scraper de Facebook iniciado. "
                f"Use GET /runs/{run_id} para consultar estado"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error iniciando scraper: {str(e)}"
        )


class SimpleScrapeRequest(BaseModel):
    url: AnyUrl = Field(..., description="URL de Ads Library a scrapear")
    count: Optional[int] = Field(default=100, ge=1)
    # timeout máximo en segundos para esperar al run
    timeout: Optional[int] = Field(default=600, ge=10)


@router.get("/runs/{run_id}", response_model=Dict)
async def get_run_status(run_id: str):
    """
    Consulta el estado de una ejecución del scraper

    Use este endpoint para monitorear el progreso del scraping.
    """
    try:
        actor = FacebookActor()
        run_data = actor.get_run_status(run_id)

        if not run_data:
            raise HTTPException(
                status_code=404, detail=f"Run {run_id} no encontrado")

        return {
            "run_id": run_id,
            "status": run_data.get("status"),
            "started_at": run_data.get("startedAt"),
            "finished_at": run_data.get("finishedAt"),
            "default_dataset_id": run_data.get("defaultDatasetId"),
            "stats": run_data.get("stats", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error consultando estado: {str(e)}")


@router.get("/runs/{run_id}/results", response_model=FacebookResponse)
async def get_run_results(
    run_id: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Cantidad máxima de anuncios a retornar"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset para paginación"
    )
):
    """
    Obtiene los resultados de una ejecución completada

    Solo funciona si el run tiene status = SUCCEEDED.
    Los datos se normalizan a un formato consistente.

    Args:
        run_id: ID de la ejecución
        limit: Cantidad máxima de items (1-1000)
        offset: Offset para paginación

    Returns:
        FacebookResponse con los anuncios scrapeados y normalizados
    """
    try:
        actor = FacebookActor()

        try:
            # Obtener resultados
            run_data, items = actor.get_results(
                run_id=run_id,
                limit=limit,
                offset=offset
            )

            # Normalizar
            normalized_data = [
                FacebookActor.normalize_ad(item) for item in items
            ]

            return FacebookResponse(
                status="success",
                run_id=run_id,
                actor_status=run_data.get("status") if run_data else None,
                count=len(normalized_data),
                data=normalized_data
            )

        except ValueError as e:
            # Error de validación (no tiene dataset, estado inválido)
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
    Verifica que el servicio Facebook esté configurado correctamente
    """
    try:
        actor = FacebookActor()

        return {
            "status": "healthy",
            "service": "Facebook Ads Library Scraper",
            "actor_id": actor.actor_id,
            "configured": bool(actor.actor_id and actor.token)
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "Facebook Ads Library Scraper",
            "error": str(e)
        }


@router.post('/runs/{run_id}/preparer', status_code=200)
async def preparer_run(
    run_id: str,
    top: int = 10,
    method: str = 'heuristic',
    max_dim: int = 512,
    jpeg_quality: int = 70,
    limit_per_ad: int = 5,
    numeric_size: int = 128,
    drive_folder_id: Optional[str] = None,
):
    """Prepara las imágenes de los top-N anuncios para análisis.

    Flujo:
    - calcula top-N usando el analizador
    - localiza los archivos de media para esos ad_ids en
      datasets/saved_datasets/facebook/<run_id>/media/
    - para cada archivo (hasta limit_per_ad por ad):
      * redimensiona (max_dim)
      * guarda versión en escala de grises (JPEG)
      * genera un "heatmap" simple (PNG)
      * extrae paleta de colores (6 colores) y la añade al metadata
    - empaqueta todos los artefactos en
      datasets/saved_datasets/facebook/<run_id>/prepared/<run_id>_top{top}_prepared.zip

    Retorna la ruta del ZIP y un resumen por ad.
    """
    try:
        from pathlib import Path
        import json
        import shutil

        base = get_facebook_saved_base()
        run_dir = base / run_id
        if not run_dir.exists():
            raise HTTPException(
                status_code=404, detail=f'Run dir not found: {run_dir}')

        csv_path = run_dir / f'{run_id}.csv'
        jsonl_path = run_dir / f'{run_id}.jsonl'

        stats = {}
        if csv_path.exists():
            stats = analyze(csv_path, method=method)
        elif jsonl_path.exists():
            stats = analyze_jsonl(jsonl_path, method=method)
        else:
            raise HTTPException(
                status_code=404, detail='No CSV or JSONL dataset found for this run')

        items = sorted(stats.values(), key=lambda x: x.get(
            'score', 0), reverse=True)
        top_items = items[:top]
        top_ads = [it.get('ad_id') for it in top_items]

        media_dir = run_dir / 'media'

        # prepared folder will contain copies of the selected top files (images/videos) as-is
        prepared_base = run_dir / 'prepared'
        prepared_base.mkdir(parents=True, exist_ok=True)

        summary = {}
        manifest = {'run_id': run_id, 'top': top, 'ads': []}

        # For each top ad, copy up to limit_per_ad original media files into prepared/<ad>/
        for ad in top_ads:
            summary[ad] = {'processed': 0, 'files': []}
            manifest_ad = {'ad_id': ad, 'files': []}
            if not media_dir.exists():
                manifest['ads'].append(manifest_ad)
                continue
            matched = [p for p in media_dir.iterdir() if p.is_file()
                       and p.name.startswith(str(ad or ''))]
            ad_prepared_dir = prepared_base / str(ad)
            ad_prepared_dir.mkdir(parents=True, exist_ok=True)

            for p in matched[:limit_per_ad]:
                try:
                    dest = ad_prepared_dir / p.name
                    # copy the original file as-is
                    shutil.copy2(p, dest)

                    entry = {
                        'source': p.name,
                        'prepared_path': str(dest)
                    }
                    manifest_ad['files'].append(entry)
                    summary[ad]['processed'] += 1
                    summary[ad]['files'].append(entry)
                except Exception:
                    # continue on per-file errors
                    continue

            manifest['ads'].append(manifest_ad)

        # write manifest JSON
        json_path = prepared_base / f'{run_id}_top{top}_prepared.json'
        with json_path.open('w', encoding='utf-8') as jf:
            json.dump(manifest, jf, ensure_ascii=False, indent=2)

        # If a drive_folder_id was provided, start background upload (same behavior as before)
        upload_started = False
        if drive_folder_id and drive_service is not None:
            try:
                asyncio.create_task(_upload_top_task(
                    run_id=run_id, top=top, folder_id=drive_folder_id, limit_per_ad=limit_per_ad))
                upload_started = True
            except Exception:
                upload_started = False

        return {
            'status': 'ok',
            'run_id': run_id,
            'top': top,
            'prepared_json': str(json_path),
            'summary': summary,
            'upload_started': upload_started,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _upload_top_task(run_id: str, top: int, folder_id: str, limit_per_ad: int = 5):
    """
    Tarea asíncrona que sube los archivos de media (imágenes y videos)
    de los top-N anuncios a Google Drive usando `drive_service`.
    """
    try:
        if drive_service is None:
            print("DriveService no disponible: imposible subir archivos")
            return

        from pathlib import Path

        base = get_facebook_saved_base()
        run_dir = base / run_id
        if not run_dir.exists():
            print(f"Run dir not found: {run_dir}")
            return

        csv_path = run_dir / f'{run_id}.csv'
        jsonl_path = run_dir / f'{run_id}.jsonl'

        stats = {}
        if csv_path.exists():
            stats = analyze(csv_path)
        elif jsonl_path.exists():
            stats = analyze_jsonl(jsonl_path)
        else:
            print('No CSV or JSONL dataset found for upload task')
            return

        items = sorted(stats.values(), key=lambda x: x.get(
            'score', 0), reverse=True)
        top_items = items[:top]
        top_ads = [it.get('ad_id') for it in top_items]

        media_dir = run_dir / 'media'

        for ad in top_ads:
            if not media_dir.exists():
                continue
            matched = [p for p in media_dir.iterdir() if p.is_file()
                       and p.name.startswith(str(ad or ''))]
            for p in matched[:limit_per_ad]:
                try:
                    # usar drive_service para subir desde la URL si p is remote URL stored;
                    # en este proyecto media files are local, así que subimos archivo local
                    # si el archivo es local, usar upload_local_file
                    result = drive_service.upload_local_file(
                        file_path=str(p),
                        filename=f"{ad} - {p.stem}",
                        folder_id=folder_id
                    )
                    # drive_service.upload_from_url es async; si devuelve coroutine, await
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    print(f"Error subiendo {p}: {e}")

    except Exception as e:
        # Registrar el error de la tarea asíncrona y terminar la tarea
        print(f"_upload_top_task error: {e}")
        return


@router.post('/runs/{run_id}/upload_top', status_code=202)
async def upload_top_run(run_id: str, top: int = 10, folder_id: Optional[str] = Query(None), limit_per_ad: int = 5):
    """
    Endpoint para iniciar la subida de los top-N anuncios (imágenes y videos)
    a una carpeta de Google Drive. La subida se realiza en background.
    """
    try:
        if drive_service is None:
            raise HTTPException(
                status_code=503, detail='Drive service not configured')

        # Si no se pasó folder_id en la petición, tomarla de la variable de entorno
        if not folder_id:
            folder_id = os.getenv('GOOGLE_PATH_ID')

        if not folder_id:
            raise HTTPException(
                status_code=400, detail='folder_id not provided and GOOGLE_PATH_ID not set')

        # Iniciar tarea en background
        asyncio.create_task(_upload_top_task(
            run_id=run_id, top=top, folder_id=folder_id, limit_per_ad=limit_per_ad))

        return {'status': 'started', 'run_id': run_id, 'top': top, 'folder_id': folder_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/runs/{run_id}/upload_top_env', status_code=200)
async def upload_top_run_env(run_id: str, top: int = 10, limit_per_ad: int = 5):
    """
    Sube síncronamente los archivos de los top-N anuncios a la carpeta indicada
    en la variable de entorno `GOOGLE_PATH_ID` y devuelve las URLs públicas.

    Flujo:
    - usa `analyze` / `analyze_jsonl` para obtener top-N
    - sube los archivos locales encontrados en `media/` para esos ads (hasta limit_per_ad)
    - devuelve un listado con el resultado por archivo (url o error)
    """
    try:
        if drive_service is None:
            raise HTTPException(
                status_code=503, detail='Drive service not configured')

        folder_id = os.getenv('GOOGLE_PATH_ID')
        if not folder_id:
            raise HTTPException(
                status_code=400, detail='GOOGLE_PATH_ID not set in environment')

        from pathlib import Path

        base = get_facebook_saved_base()
        run_dir = base / run_id
        if not run_dir.exists():
            raise HTTPException(
                status_code=404, detail=f'Run dir not found: {run_dir}')

        csv_path = run_dir / f'{run_id}.csv'
        jsonl_path = run_dir / f'{run_id}.jsonl'

        stats = {}
        if csv_path.exists():
            stats = analyze(csv_path)
        elif jsonl_path.exists():
            stats = analyze_jsonl(jsonl_path)
        else:
            raise HTTPException(
                status_code=404, detail='No CSV or JSONL dataset found for this run')

        items = sorted(stats.values(), key=lambda x: x.get(
            'score', 0), reverse=True)
        top_items = items[:top]
        top_ads = [it.get('ad_id') for it in top_items]

        media_dir = run_dir / 'media'
        results = []

        for ad in top_ads:
            if not media_dir.exists():
                continue
            matched = [p for p in media_dir.iterdir() if p.is_file()
                       and p.name.startswith(str(ad or ''))]
            for p in matched[:limit_per_ad]:
                try:
                    # llamar al servicio para subir y esperar resultado
                    upload_res = await drive_service.upload_local_file(
                        file_path=str(p),
                        filename=f"{ad} - {p.stem}",
                        folder_id=folder_id,
                    )

                    entry = {
                        'source_file': str(p),
                        'ad_id': ad,
                        'result': upload_res,
                    }
                    results.append(entry)
                except Exception as e:
                    results.append(
                        {'source_file': str(p), 'ad_id': ad, 'error': str(e)})

        return {'status': 'ok', 'run_id': run_id, 'uploaded': results}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/runs/{run_id}/prepare_and_upload', status_code=200)
async def prepare_and_upload(
    run_id: str,
    top: int = 10,
    method: str = 'heuristic',
    max_dim: int = 512,
    jpeg_quality: int = 70,
    limit_per_ad: int = 5,
    numeric_size: int = 128,
    folder_id: Optional[str] = None,
):
    """
    Ejecuta todo el flujo: prepara los artefactos (grayscale/heatmap/palette/numeric)
    y a continuación sube los archivos de los top-N anuncios a la carpeta de Drive
    indicada por `folder_id` (o por la variable de entorno `GOOGLE_PATH_ID` si no se
    pasa). Devuelve el resumen de la preparación y el listado de resultados de subida.
    """
    try:
        # 1) Preparar (no iniciar upload en background desde preparer_run)
        prep = await preparer_run(
            run_id=run_id,
            top=top,
            method=method,
            max_dim=max_dim,
            jpeg_quality=jpeg_quality,
            limit_per_ad=limit_per_ad,
            numeric_size=numeric_size,
            drive_folder_id=None,
        )

        # 2) Determinar carpeta de Drive
        if folder_id is None:
            folder_id = os.getenv('GOOGLE_PATH_ID')
        if not folder_id:
            raise HTTPException(
                status_code=400, detail='folder_id not provided and GOOGLE_PATH_ID not set')

        # 3) Subir sincronamente (mismo comportamiento que upload_top_run_env pero con folder_id)
        if drive_service is None:
            raise HTTPException(
                status_code=503, detail='Drive service not configured')

        from pathlib import Path

        base = get_facebook_saved_base()
        run_dir = base / run_id
        if not run_dir.exists():
            raise HTTPException(
                status_code=404, detail=f'Run dir not found: {run_dir}')

        csv_path = run_dir / f'{run_id}.csv'
        jsonl_path = run_dir / f'{run_id}.jsonl'

        stats = {}
        if csv_path.exists():
            stats = analyze(csv_path)
        elif jsonl_path.exists():
            stats = analyze_jsonl(jsonl_path)
        else:
            raise HTTPException(
                status_code=404, detail='No CSV or JSONL dataset found for this run')

        items = sorted(stats.values(), key=lambda x: x.get(
            'score', 0), reverse=True)
        top_items = items[:top]
        top_ads = [it.get('ad_id') for it in top_items]

        media_dir = run_dir / 'media'
        results = []

        for ad in top_ads:
            if not media_dir.exists():
                continue
            matched = [p for p in media_dir.iterdir() if p.is_file()
                       and p.name.startswith(str(ad or ''))]
            for p in matched[:limit_per_ad]:
                try:
                    upload_res = await drive_service.upload_local_file(
                        file_path=str(p),
                        filename=f"{ad} - {p.stem}",
                        folder_id=folder_id,
                    )
                    results.append(
                        {'source_file': str(p), 'ad_id': ad, 'result': upload_res})
                except Exception as e:
                    results.append(
                        {'source_file': str(p), 'ad_id': ad, 'error': str(e)})

        return {'status': 'ok', 'run_id': run_id, 'prepared': prep, 'uploaded': results}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# GCS UPLOAD ENDPOINTS
# ==========================================

@router.post('/runs/{run_id}/upload_to_gcs', status_code=200)
async def upload_prepared_to_gcs(
    run_id: str,
    bucket_name: Optional[str] = None,
    prefix: Optional[str] = None
):
    """
    Sube el contenido de la carpeta prepared/ a Google Cloud Storage.

    Args:
        run_id: ID del run a subir
        bucket_name: Nombre del bucket (opcional, usa GOOGLE_BUCKET_NAME por defecto)
        prefix: Prefijo para organizar en el bucket (por defecto: runs/{run_id}/prepared/)

    Returns:
        Lista de archivos subidos con sus URLs públicas
    """
    try:
        if gcs_service is None:
            raise HTTPException(
                status_code=503,
                detail='GCS service not configured. Set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_BUCKET_NAME'
            )

        from pathlib import Path
        import json

        base = get_facebook_saved_base()
        run_dir = base / run_id

        if not run_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f'Run directory not found: {run_dir}'
            )

        prepared_dir = run_dir / 'prepared'
        if not prepared_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f'Prepared directory not found. Run prepare endpoint first for run_id: {run_id}'
            )

        # Prefijo por defecto en el bucket
        if prefix is None:
            prefix = f'runs/{run_id}/prepared'

        results = []

        # Subir manifest.json si existe
        manifest_path = prepared_dir / 'manifest.json'
        if manifest_path.exists():
            blob_name = f'{prefix}/manifest.json'
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_content = f.read()

                upload_res = gcs_service.upload_string(
                    content=manifest_content,
                    blob_name=blob_name,
                    bucket_name=bucket_name,
                    content_type='application/json'
                )
                results.append({
                    'type': 'manifest',
                    'source_file': str(manifest_path),
                    'blob_name': blob_name,
                    'public_url': upload_res['public_url'],
                    'size': upload_res['size']
                })
            except Exception as e:
                results.append({
                    'type': 'manifest',
                    'source_file': str(manifest_path),
                    'error': str(e)
                })

        # Subir archivos de medios organizados por ad_id
        for ad_folder in prepared_dir.iterdir():
            if not ad_folder.is_dir():
                continue

            ad_id = ad_folder.name

            for media_file in ad_folder.iterdir():
                if not media_file.is_file():
                    continue

                # Construir blob_name: runs/{run_id}/prepared/{ad_id}/{filename}
                blob_name = f'{prefix}/{ad_id}/{media_file.name}'

                try:
                    # Detectar content_type basado en extensión
                    ext = media_file.suffix.lower()
                    content_type = None
                    if ext in ['.jpg', '.jpeg']:
                        content_type = 'image/jpeg'
                    elif ext == '.png':
                        content_type = 'image/png'
                    elif ext == '.mp4':
                        content_type = 'video/mp4'
                    elif ext == '.webm':
                        content_type = 'video/webm'

                    upload_res = gcs_service.upload_file(
                        local_path=str(media_file),
                        blob_name=blob_name,
                        bucket_name=bucket_name,
                        content_type=content_type
                    )

                    results.append({
                        'type': 'media',
                        'ad_id': ad_id,
                        'source_file': str(media_file),
                        'blob_name': blob_name,
                        'public_url': upload_res['public_url'],
                        'size': upload_res['size']
                    })
                except Exception as e:
                    results.append({
                        'type': 'media',
                        'ad_id': ad_id,
                        'source_file': str(media_file),
                        'blob_name': blob_name,
                        'error': str(e)
                    })

        # Contar resultados
        success_count = len([r for r in results if 'error' not in r])
        error_count = len([r for r in results if 'error' in r])

        return {
            'status': 'ok',
            'run_id': run_id,
            'bucket': bucket_name or gcs_service.default_bucket_name,
            'prefix': prefix,
            'uploaded': results,
            'summary': {
                'total': len(results),
                'success': success_count,
                'errors': error_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/runs/{run_id}/prepare_and_upload_gcs', status_code=200)
async def prepare_and_upload_gcs(
    run_id: str,
    top: int = 10,
    limit_per_ad: int = 5,
    bucket_name: Optional[str] = None,
    prefix: Optional[str] = None
):
    """
    Ejecuta el flujo completo: prepara los archivos (copia top-N) y los sube a GCS.

    Args:
        run_id: ID del run
        top: Número de anuncios top a preparar
        limit_per_ad: Límite de archivos por anuncio
        bucket_name: Nombre del bucket GCS (opcional)
        prefix: Prefijo en el bucket (por defecto: runs/{run_id}/prepared/)

    Returns:
        Resumen de la preparación y subida a GCS
    """
    try:
        # 1) Preparar archivos
        prep = await preparer_run(
            run_id=run_id,
            top=top,
            method='heuristic',  # No usado pero requerido
            max_dim=512,  # No usado
            jpeg_quality=70,  # No usado
            limit_per_ad=limit_per_ad,
            numeric_size=128,  # No usado
            drive_folder_id=None,  # No subir a Drive
        )

        # 2) Subir a GCS
        upload_result = await upload_prepared_to_gcs(
            run_id=run_id,
            bucket_name=bucket_name,
            prefix=prefix
        )

        return {
            'status': 'ok',
            'run_id': run_id,
            'prepared': prep,
            'gcs_upload': upload_result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/scrape_prepare_upload_gcs', status_code=202, tags=["Facebook"])
async def scrape_prepare_upload_gcs(
    url: str,
    count: int = 100,
    top: int = 10,
    limit_per_ad: int = 5,
    timeout: int = 600,
    bucket_name: Optional[str] = None,
    prefix: Optional[str] = None
):
    """
    Flujo completo end-to-end: Scrape → Prepare → Upload a GCS

    Desde una URL de Meta Ads Library:
    1. Inicia el scraper en Apify
    2. Espera a que termine (con timeout)
    3. Descarga y guarda el dataset localmente
    4. Descarga las imágenes/videos de los top-N anuncios
    5. Prepara los archivos (selecciona top-N)
    6. Sube todo a Google Cloud Storage
    7. Retorna URLs de los archivos en GCS

    Args:
        url: URL de Meta Ads Library (ej: https://www.facebook.com/ads/library/?...)
        count: Número máximo de anuncios a scrapear (default: 100)
        top: Número de mejores anuncios a preparar y subir (default: 10)
        limit_per_ad: Máximo de archivos multimedia por anuncio (default: 5)
        timeout: Timeout en segundos para esperar al scraper (default: 600 = 10 min)
        bucket_name: Nombre del bucket GCS (opcional, usa GOOGLE_BUCKET_NAME)
        prefix: Prefijo en el bucket (default: runs/{run_id}/prepared/)

    Returns:
        Información completa del proceso: run_id, dataset, archivos subidos, URLs de GCS
    """
    try:
        # Validar que GCS esté configurado
        if gcs_service is None:
            raise HTTPException(
                status_code=503,
                detail='GCS service not configured. Set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_BUCKET_NAME'
            )

        # PASO 1: Iniciar scraper de Apify
        actor = FacebookActor()

        actor_input = {
            "count": int(count),
            "scrapeAdDetails": True,
            "urls": [{"url": url}],
        }

        run_data = await asyncio.to_thread(actor.run_async, actor_input)

        if not run_data or not run_data.get("id"):
            raise HTTPException(
                status_code=500,
                detail="No se pudo iniciar el actor de Facebook"
            )

        run_id = str(run_data.get("id"))

        # PASO 2: Esperar a que termine el scraper
        poll_interval = 5
        elapsed = 0

        while elapsed < timeout:
            status_data = await asyncio.to_thread(actor.get_run_status, run_id)
            status = status_data.get("status") if status_data else None

            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "ABORTED"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Scraper finalizó con estado {status}"
                )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        if elapsed >= timeout:
            raise HTTPException(
                status_code=504,
                detail=f"Timeout esperando al scraper ({timeout}s)"
            )

        # PASO 3: Descargar y guardar dataset
        meta = fetch_and_store_run_dataset(run_id)

        # PASO 4: Analizar y descargar imágenes de top-N
        from pathlib import Path

        base = get_facebook_saved_base()
        run_dir = base / run_id

        csv_path = run_dir / f'{run_id}.csv'
        jsonl_path = run_dir / f'{run_id}.jsonl'

        stats = {}
        if csv_path.exists():
            stats = analyze(csv_path)
        elif jsonl_path.exists():
            stats = analyze_jsonl(jsonl_path)
        else:
            raise HTTPException(
                status_code=404,
                detail='No se pudo generar el dataset'
            )

        items = sorted(stats.values(), key=lambda x: x.get(
            'score', 0), reverse=True)
        top_items = items[:top]
        top_ads = [it.get('ad_id') for it in top_items]

        # Descargar medios
        media_dir = run_dir / 'media'
        media_dir.mkdir(parents=True, exist_ok=True)
        session = make_session()

        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = []

            if csv_path.exists():
                for row, snapshot in iter_csv_snapshot_rows(csv_path):
                    ad_id = row.get("ad_archive_id") or row.get(
                        "ad_id") or "unknown"
                    if ad_id not in top_ads:
                        continue
                    if not snapshot:
                        continue
                    urls = extract_urls_from_snapshot(snapshot)
                    for u in urls:
                        futures.append(
                            ex.submit(download_one, session, u,
                                      media_dir, prefix=ad_id)
                        )
            else:
                import json
                with jsonl_path.open("r", encoding="utf-8") as jf:
                    for line in jf:
                        try:
                            item = json.loads(line)
                        except Exception:
                            continue
                        ad_id = (
                            item.get("ad_archive_id") or
                            item.get("adArchiveID") or
                            item.get("id") or
                            "unknown"
                        )
                        if ad_id not in top_ads:
                            continue
                        snap = item.get("snapshot") or {}
                        if not isinstance(snap, dict):
                            continue
                        urls = extract_urls_from_snapshot(snap)
                        for u in urls:
                            futures.append(
                                ex.submit(download_one, session, u,
                                          media_dir, prefix=ad_id)
                            )

            downloaded = 0
            failures = 0
            for fut in as_completed(futures):
                url_result, path = fut.result()
                if path:
                    downloaded += 1
                else:
                    failures += 1

        # PASO 5: Preparar archivos
        prep = await preparer_run(
            run_id=run_id,
            top=top,
            method='heuristic',
            max_dim=512,
            jpeg_quality=70,
            limit_per_ad=limit_per_ad,
            numeric_size=128,
            drive_folder_id=None,
        )

        # PASO 6: Subir a GCS
        upload_result = await upload_prepared_to_gcs(
            run_id=run_id,
            bucket_name=bucket_name,
            prefix=prefix
        )

        # PASO 7: Obtener URLs de los archivos subidos
        gcs_files = await get_run_gcs_files(
            run_id=run_id,
            generate_signed_urls=True,
            expiration_hours=24
        )

        return {
            'status': 'success',
            'message': 'Scraping, preparation and upload to GCS completed',
            'run_id': run_id,
            'scraper': {
                'url': url,
                'count': count,
                'elapsed_seconds': elapsed
            },
            'dataset': {
                'total_ads': len(stats),
                'top_ads': top_ads,
                'downloaded_media': downloaded,
                'download_failures': failures,
                'metadata': meta
            },
            'prepared': prep,
            'gcs_upload': upload_result,
            'gcs_files': gcs_files,
            'bucket_url': f"https://console.cloud.google.com/storage/browser/{bucket_name or gcs_service.default_bucket_name}/runs/{run_id}/prepared/"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/latest/gcs_manifest", tags=["Facebook"])
async def get_latest_run_gcs_manifest(
    expiration_hours: int = Query(
        24, ge=1, le=168,
        description="URL expiration in hours (1-168)"
    )
):
    """
    Obtiene automáticamente el último run_id y devuelve un JSON estructurado
    con todas las URLs firmadas de los archivos en GCS, listo para usar.

    Ejemplo de respuesta:
    {
      "run_id": "qZ1oP0Up0UhhyL30G",
      "created_at": "2025-11-07T21:14:00Z",
      "url_expiration_hours": 24,
      "total_ads": 10,
      "total_files": 50,
      "ads": [
        {
          "ad_id": "1606880380741561",
          "media_count": 5,
          "media_urls": [
            "https://storage.googleapis.com/...",
            ...
          ]
        },
        ...
      ],
      "bucket_url": "https://console.cloud.google.com/..."
    }
    """
    try:
        # Obtener el último run_id
        saved_base = get_facebook_saved_base()
        if not saved_base.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Dataset directory not found: {saved_base}"
            )

        # Listar todos los runs
        run_dirs = [
            d for d in saved_base.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]

        if not run_dirs:
            raise HTTPException(
                status_code=404,
                detail="No saved runs found"
            )

        # Ordenar por fecha de modificación (más reciente primero)
        run_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_run_id = run_dirs[0].name

        # Obtener archivos del GCS
        gcs_files = await get_run_gcs_files(
            run_id=latest_run_id,
            generate_signed_urls=True,
            expiration_hours=expiration_hours
        )

        if gcs_files['status'] != 'success':
            raise HTTPException(
                status_code=404,
                detail=f"No files found in GCS for run {latest_run_id}"
            )

        # Preparar el manifest estructurado
        ads_manifest = []
        for ad_id, media_files in gcs_files['media_by_ad'].items():
            ads_manifest.append({
                'ad_id': ad_id,
                'media_count': len(media_files),
                'media_urls': [file['url'] for file in media_files]
            })

        # Obtener fecha de creación del run
        created_at = run_dirs[0].stat().st_mtime
        from datetime import datetime
        created_datetime = datetime.fromtimestamp(created_at).isoformat() + 'Z'

        manifest = {
            'run_id': latest_run_id,
            'created_at': created_datetime,
            'url_expiration_hours': expiration_hours,
            'total_ads': len(ads_manifest),
            'total_files': sum(
                len(files) for files in gcs_files['media_by_ad'].values()
            ),
            'ads': ads_manifest,
            'bucket_url': (
                f"https://console.cloud.google.com/storage/browser/"
                f"{gcs_files['bucket']}/runs/{latest_run_id}/prepared/"
            )
        }

        return manifest

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runs/save_manifest", tags=["Facebook"])
async def save_run_manifest(
    run_id: Optional[str] = Query(
        None,
        description="Run ID to save (if None, uses latest)"
    ),
    expiration_hours: int = Query(
        24, ge=1, le=168,
        description="URL expiration in hours (1-168)"
    ),
    output_filename: str = Query(
        "manifest.json",
        description="Output filename"
    )
):
    """
    Guarda el manifest de un run (o el último run) como un archivo JSON local.

    El archivo se guarda en la carpeta del run correspondiente.

    Returns:
        {
            "status": "success",
            "run_id": "qZ1oP0Up0UhhyL30G",
            "manifest_path": "/path/to/run/manifest.json",
            "manifest": { ... }
        }
    """
    try:
        # Si no se especifica run_id, obtener el último
        if not run_id:
            saved_base = get_facebook_saved_base()
            if not saved_base.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Dataset directory not found: {saved_base}"
                )

            run_dirs = [
                d for d in saved_base.iterdir()
                if d.is_dir() and not d.name.startswith('.')
            ]

            if not run_dirs:
                raise HTTPException(
                    status_code=404,
                    detail="No saved runs found"
                )

            run_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            run_id = run_dirs[0].name

        # Obtener el manifest
        saved_base = get_facebook_saved_base()
        run_dir = saved_base / run_id

        if not run_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Run directory not found: {run_id}"
            )

        # Obtener archivos del GCS
        gcs_files = await get_run_gcs_files(
            run_id=run_id,
            generate_signed_urls=True,
            expiration_hours=expiration_hours
        )

        if gcs_files['status'] != 'success':
            raise HTTPException(
                status_code=404,
                detail=f"No files found in GCS for run {run_id}"
            )

        # Preparar el manifest estructurado
        ads_manifest = []
        for ad_id, media_files in gcs_files['media_by_ad'].items():
            ads_manifest.append({
                'ad_id': ad_id,
                'media_count': len(media_files),
                'media_urls': [file['url'] for file in media_files]
            })

        # Obtener fecha de creación del run
        created_at = run_dir.stat().st_mtime
        from datetime import datetime
        created_datetime = datetime.fromtimestamp(created_at).isoformat() + 'Z'

        manifest = {
            'run_id': run_id,
            'created_at': created_datetime,
            'url_expiration_hours': expiration_hours,
            'total_ads': len(ads_manifest),
            'total_files': sum(
                len(files) for files in gcs_files['media_by_ad'].values()
            ),
            'ads': ads_manifest,
            'bucket_url': (
                f"https://console.cloud.google.com/storage/browser/"
                f"{gcs_files['bucket']}/runs/{run_id}/prepared/"
            )
        }

        # Guardar el manifest en el directorio del run
        manifest_path = run_dir / output_filename
        import json
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return {
            'status': 'success',
            'run_id': run_id,
            'manifest_path': str(manifest_path),
            'manifest': manifest
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# INTEGRACIÓN DE MÓDULOS
# ==========================================

# Importar y configurar módulos
# ============================================================================
# ENDPOINT COMPLETO: ANÁLISIS DE CAMPAÑA CON GEMINI AI
# ============================================================================

class AnalyzeCampaignRequest(BaseModel):
    """Request para análisis completo de campaña con Gemini

    Se acepta EITHER una `manifest_url` pública (JSON en GCS) O un
    `run_id` de Apify. Si se provee `run_id`, el endpoint obtendrá los
    resultados directamente desde el actor de Apify.
    """
    manifest_url: Optional[str] = Field(
        None,
        description="URL pública del manifest JSON desde GCS. Opcional si se proporciona run_id."
    )
    run_id: Optional[str] = Field(
        None,
        description="(Opcional) Apify run id. Si se provee, se obtienen resultados directamente del actor."
    )


@router.post(
    '/analyze-campaign-with-ai',
    tags=["ai-analysis", "gemini"],
    summary="🤖 Análisis Completo de Campaña con IA"
)
async def analyze_campaign_with_ai(request: AnalyzeCampaignRequest):
    """
    🎯 ENDPOINT COMPLETO - Análisis automático de campaña publicitaria con Gemini AI

    Este endpoint realiza TODO el proceso automáticamente:
    1. ✅ Descarga el manifest JSON desde la URL pública (GCS)
    2. ✅ Analiza cada anuncio con Gemini AI como experto en marketing
    3. ✅ Determina cuál anuncio tuvo mejor rendimiento y por qué
    4. ✅ Genera y guarda reporte JSON detallado en reports_json/
    5. ✅ Retorna el análisis completo

    El análisis incluye evaluación de:
    - Composición visual y paleta de colores
    - Elementos, objetos y contexto
    - Tipografía y legibilidad del mensaje
    - Contenido multimedia (duración, ritmo, música)
    - Psicología del marketing y persuasión
    - Rendimiento estimado (CTR, engagement, viralidad)
    - Recomendaciones para futuras campañas

    Args:
        request: {
            "manifest_url": "https://storage.googleapis.com/.../manifest.json",
            "run_id": "opcional_run_id"
        }

    Returns:
        {
            "status": "success",
            "run_id": "...",
            "manifest_downloaded": true,
            "total_ads_analyzed": 10,
            "report_path": "reports_json/..._analysis_20251107_143022.json",
            "report_filename": "...",
            "analysis_summary": {
                "best_performer": { "ad_id": "...", "overall_score": 9.5 },
                "generated_at": "..."
            },
            "full_analysis": { ... }
        }

    Example:
        POST /api/v1/apify/facebook/analyze-campaign-with-ai
        {
            "manifest_url": "https://storage.googleapis.com/proveedor-1/facebook/yHAmj34fDeR94qUrh/prepared/manifest.json"
        }

    Time: 30-90 segundos (análisis profundo con IA)
    """

    # Verificar que Gemini esté disponible
    try:
        from app.services.gemini_service import GeminiService
        gemini_service = GeminiService()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Gemini AI service not available: {str(e)}. "
                   "Verifica GOOGLE_GEMINI_API en .env"
        )

    try:
        import httpx
        import json
        from urllib.parse import urlparse, parse_qs

        manifest_data = None

        # Si se pasa run_id explícito, obtener resultados desde Apify
        if request.run_id:
            run_id = request.run_id
            try:
                actor = FacebookActor()
                run_data, items = actor.get_results(run_id=run_id, limit=10000)
            except Exception as e2:
                raise HTTPException(
                    status_code=400,
                    detail=(f"Failed to retrieve run results from Apify for run_id={run_id}: {str(e2)}. "
                            "Puedes listar runs con GET /api/v1/apify/general/runs to find the run_id.")
                )

            # Construir manifest simplificado
            manifest_data = {"run_id": run_id, "ads": []}
            for it in items:
                ad_id = it.get('ad_archive_id') or it.get(
                    'id') or it.get('ad_id') or ''
                files = []
                for k, v in it.items():
                    try:
                        if isinstance(v, str) and v.startswith('http'):
                            lower = v.lower()
                            if lower.endswith('.mp4') or 'video' in lower:
                                ftype = 'video'
                            elif lower.endswith('.jpg') or lower.endswith('.jpeg') or lower.endswith('.png') or 'image' in lower:
                                ftype = 'image'
                            else:
                                ftype = 'unknown'
                            files.append(
                                {'url': v, 'type': ftype, 'source_key': k})
                    except Exception:
                        continue
                manifest_data['ads'].append({'ad_id': ad_id or str(
                    len(manifest_data['ads'])+1), 'files': files})

        else:
            # Si no se pasó run_id, intentar descargar manifest desde la URL
            if not request.manifest_url:
                raise HTTPException(
                    status_code=400,
                    detail="Se requiere manifest_url o run_id en el request"
                )

            # Si la URL es una Facebook Ads Library URL, reutilizar el workflow
            # existente que scrappea/prepara y sube a GCS. Esto evita duplicar
            # la lógica y usa código ya validado.
            try:
                if ('facebook.com' in str(request.manifest_url).lower()
                        or 'ads/library' in str(request.manifest_url).lower()):
                    from .modules import workflow as workflow_module

                    # Ejecutar workflow end-to-end reutilizando la lógica
                    workflow_res = await workflow_module.scrape_prepare_and_upload_to_gcs(
                        url=request.manifest_url,
                        count=100,
                        top=10,
                        limit_per_ad=5,
                        bucket_name=None,
                        prefix=None,
                        timeout=300
                    )

                    # Extraer gcs_files y construir manifest_data a partir de URLs firmadas
                    gcs_files = workflow_res.get(
                        'gcs_files') or workflow_res.get('gcs_files', {})
                    media_by_ad = gcs_files.get(
                        'media_by_ad', {}) if isinstance(gcs_files, dict) else {}
                    manifest_data = {"run_id": workflow_res.get(
                        'run_id') or 'unknown', 'ads': []}
                    for ad_id, media_files in media_by_ad.items():
                        files = []
                        for f in media_files:
                            files.append({'url': f.get('url') or f.get('public_url') or f.get('blob_name'),
                                          'type': 'video' if (f.get('contentType') and 'video' in f.get('contentType')) else 'image'})
                        manifest_data['ads'].append(
                            {'ad_id': ad_id, 'files': files})

                    # Continuar con el análisis usando manifest_data
                    pass
            except Exception:
                # Si el workflow falla, seguimos con el flujo de fallback
                manifest_data = None

            # Detectar si manifest_url es en realidad un run_id simple (sin scheme)
            parsed_quick = urlparse(str(request.manifest_url))
            candidate_simple = parsed_quick.path.strip(
                '/') if parsed_quick.path else str(request.manifest_url)
            if (not parsed_quick.scheme and candidate_simple and len(candidate_simple) > 5
                    and all(c.isalnum() or c in ('-', '_') for c in candidate_simple)):
                # tratar candidate_simple como run_id
                run_id = candidate_simple
                try:
                    actor = FacebookActor()
                    run_data, items = actor.get_results(
                        run_id=run_id, limit=10000)
                except Exception as e2:
                    raise HTTPException(
                        status_code=400,
                        detail=(f"Failed to retrieve run results from Apify for run_id={run_id}: {str(e2)}. "
                                "Puedes listar runs con GET /api/v1/apify/general/runs to find the run_id.")
                    )

                manifest_data = {"run_id": run_id, "ads": []}
                for it in items:
                    ad_id = it.get('ad_archive_id') or it.get(
                        'id') or it.get('ad_id') or ''
                    files = []
                    for k, v in it.items():
                        try:
                            if isinstance(v, str) and v.startswith('http'):
                                lower = v.lower()
                                if lower.endswith('.mp4') or 'video' in lower:
                                    ftype = 'video'
                                elif lower.endswith('.jpg') or lower.endswith('.jpeg') or lower.endswith('.png') or 'image' in lower:
                                    ftype = 'image'
                                else:
                                    ftype = 'unknown'
                                files.append(
                                    {'url': v, 'type': ftype, 'source_key': k})
                        except Exception:
                            continue
                    manifest_data['ads'].append({'ad_id': ad_id or str(
                        len(manifest_data['ads'])+1), 'files': files})

            else:
                # Intentar descargar el manifest desde la URL
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(request.manifest_url)
                    if response.status_code != 200:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to download manifest from URL: HTTP {response.status_code}"
                        )

                    try:
                        manifest_data = response.json()
                    except json.JSONDecodeError:
                        # Intentar interpretar la URL como un run/actor de Apify
                        url_text = str(request.manifest_url)
                        parsed = urlparse(url_text)
                        run_id = None

                        # 1) Buscar /runs/<id> o /run/<id> en el path
                        path_parts = [p for p in parsed.path.split('/') if p]
                        for i, part in enumerate(path_parts):
                            if part in ('runs', 'run') and i + 1 < len(path_parts):
                                candidate = path_parts[i + 1]
                                if candidate and not any(ch in candidate for ch in ('?', '&', '=')):
                                    run_id = candidate
                                    break

                        # 2) Si no, tomar el último segmento no vacío del path
                        if not run_id and path_parts:
                            candidate = path_parts[-1]
                            if candidate and not any(ch in candidate for ch in ('?', '&', '=')) and len(candidate) > 5:
                                run_id = candidate

                        # 3) Si sigue sin run_id, revisar query params comunes
                        if not run_id and parsed.query:
                            qs = parse_qs(parsed.query)
                            for key in ('runId', 'run_id', 'run', 'id'):
                                if key in qs and qs[key]:
                                    candidate = qs[key][0]
                                    if candidate and len(candidate) > 5:
                                        run_id = candidate
                                        break

                        if not run_id:
                            raise HTTPException(
                                status_code=400,
                                detail=("Invalid JSON in manifest URL and could not "
                                        "extract Apify run id from URL")
                            )

                        # Usar FacebookActor para obtener resultados del run
                        try:
                            actor = FacebookActor()
                            run_data, items = actor.get_results(
                                run_id=run_id, limit=10000)
                        except Exception as e2:
                            raise HTTPException(
                                status_code=400,
                                detail=(f"Failed to retrieve run results from Apify for run_id={run_id}: {str(e2)}. "
                                        "Puedes listar runs con GET /api/v1/apify/general/runs to find the run_id.")
                            )

                        # Construir un manifest_data simplificado a partir de items
                        manifest_data = {"run_id": run_id, "ads": []}
                        for it in items:
                            # intentar extraer identificador de anuncio
                            ad_id = it.get('ad_archive_id') or it.get(
                                'id') or it.get('ad_id') or ''
                            files = []
                            # Buscar cualquier valor tipo URL en el item
                            for k, v in it.items():
                                try:
                                    if isinstance(v, str) and v.startswith('http'):
                                        # inferir tipo por extensión
                                        lower = v.lower()
                                        if lower.endswith('.mp4') or 'video' in lower:
                                            ftype = 'video'
                                        elif lower.endswith('.jpg') or lower.endswith('.jpeg') or lower.endswith('.png') or 'image' in lower:
                                            ftype = 'image'
                                        else:
                                            ftype = 'unknown'
                                        files.append(
                                            {'url': v, 'type': ftype, 'source_key': k})
                                except Exception:
                                    continue

                            manifest_data['ads'].append({'ad_id': ad_id or str(
                                len(manifest_data['ads'])+1), 'files': files})

        # PASO 2: Validar estructura del manifest
        if 'ads' not in manifest_data:
            raise HTTPException(
                status_code=400,
                detail="Invalid manifest format: 'ads' key not found"
            )

        if len(manifest_data['ads']) == 0:
            raise HTTPException(
                status_code=400,
                detail="No ads found in manifest"
            )

        total_ads = len(manifest_data['ads'])

        # PASO 3: Determinar run_id automáticamente del manifest
        run_id = manifest_data.get('run_id', 'unknown_campaign')

        # PASO 4: Realizar análisis con Gemini AI
        result = gemini_service.analyze_ad_campaign_from_manifest(
            manifest_data=manifest_data,
            run_id=run_id
        )

        if result['status'] == 'error':
            raise HTTPException(
                status_code=500,
                detail=f"Campaign analysis failed: {result.get('error')}"
            )

        # PASO 5: Retornar resultado completo
        return {
            'status': 'success',
            'run_id': run_id,
            'manifest_downloaded': True,
            'manifest_url': request.manifest_url,
            'total_ads_analyzed': total_ads,
            'report_path': result['report_path'],
            'report_filename': result['report_filename'],
            'analysis_summary': result.get('analysis_summary', {}),
            'full_analysis': result.get('full_analysis', {}),
            'ai_metadata': {
                'model_used': gemini_service.default_model,
                'analysis_duration_estimate': '30-90 seconds'
            }
        }

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Timeout downloading manifest from URL (>30s)"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error downloading manifest: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in campaign analysis: {str(e)}"
        )


# ============================================================================
# INTEGRACIÓN DE MÓDULOS
# ============================================================================

try:
    from .modules import scraper, dataset, gcs as gcs_module, workflow

    # Inicializar servicios en módulos
    if gcs_service is not None:
        gcs_module.init_gcs_service(gcs_service)

    # Inicializar workflow solo si ambos servicios están disponibles
    try:
        if actor_facebook is not None and gcs_service is not None:
            workflow.init_workflow_dependencies(actor_facebook, gcs_service)
    except NameError:
        print("⚠️  WARNING: actor_facebook no está definido, workflow no inicializado")

    # Incluir routers de módulos
    router.include_router(scraper.router, prefix="", tags=["scraper-module"])
    router.include_router(dataset.router, prefix="", tags=["dataset-module"])
    router.include_router(gcs_module.router, prefix="", tags=["gcs-module"])
    router.include_router(workflow.router, prefix="", tags=["workflow-module"])

    print("✅ Módulos integrados exitosamente")
except Exception as e:
    print(f"⚠️  WARNING: Error al integrar módulos: {e}")
