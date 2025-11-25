"""
Módulo de GCS - Google Cloud Storage operations
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
import json
from .utils import get_facebook_saved_base

router = APIRouter()

# GCS service será importado desde el módulo principal
gcs_service = None


def init_gcs_service(service):
    """Inicializa la referencia al servicio GCS"""
    global gcs_service
    gcs_service = service


@router.get("/runs/{run_id}/gcs_files", tags=["Facebook"])
async def get_run_gcs_files(
    run_id: str,
    generate_signed_urls: bool = Query(
        False,
        description="Generate signed URLs for files"
    ),
    expiration_hours: int = Query(
        24, ge=1, le=168,
        description="URL expiration in hours (1-168)"
    )
):
    """
    Lista todos los archivos de un run en GCS.

    Args:
        run_id: ID del run
        generate_signed_urls: Generar URLs firmadas
        expiration_hours: Horas de validez de las URLs (1-168)

    Returns:
        {
            "status": "success",
            "run_id": "...",
            "bucket": "...",
            "files": [...],
            "media_by_ad": {...}
        }
    """
    try:
        if gcs_service is None:
            raise HTTPException(
                status_code=503,
                detail="GCS service not configured"
            )

        prefix = f'runs/{run_id}/prepared'
        files = gcs_service.list_files(prefix=prefix)

        if not files:
            raise HTTPException(
                status_code=404,
                detail=f"No files found for run {run_id} in GCS"
            )

        # Organizar por ad_id
        media_by_ad = {}
        manifest_file = None

        for file_info in files:
            blob_name = file_info['name']
            parts = blob_name.split('/')

            # manifest.json
            if blob_name.endswith('manifest.json'):
                file_info['type'] = 'manifest'
                manifest_file = file_info
                continue

            # Archivos de media: runs/{run_id}/prepared/{ad_id}/{filename}
            if len(parts) >= 5:
                ad_id = parts[3]
                if ad_id not in media_by_ad:
                    media_by_ad[ad_id] = []
                file_info['type'] = 'media'
                file_info['ad_id'] = ad_id
                media_by_ad[ad_id].append(file_info)

        # Generar URLs firmadas si se solicita
        if generate_signed_urls:
            for file_info in files:
                signed_url = gcs_service.generate_signed_url(
                    blob_name=file_info['name'],
                    expiration_hours=expiration_hours
                )
                file_info['url'] = signed_url

        return {
            'status': 'success',
            'run_id': run_id,
            'bucket': gcs_service.default_bucket_name,
            'prefix': prefix,
            'total_files': len(files),
            'total_ads': len(media_by_ad),
            'files': files,
            'media_by_ad': media_by_ad,
            'manifest': manifest_file
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/runs/{run_id}/upload_to_gcs', tags=["Facebook"])
async def upload_prepared_to_gcs(
    run_id: str,
    bucket_name: Optional[str] = None,
    prefix: Optional[str] = None
):
    """
    Sube el contenido de la carpeta prepared/ a Google Cloud Storage.

    Args:
        run_id: ID del run a subir
        bucket_name: Nombre del bucket (opcional)
        prefix: Prefijo en el bucket (default: runs/{run_id}/prepared/)

    Returns:
        {
            "status": "ok",
            "uploaded": [...],
            "summary": {...}
        }
    """
    try:
        if gcs_service is None:
            raise HTTPException(
                status_code=503,
                detail="GCS service not configured"
            )

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
                detail=f"Prepared directory not found for run_id: {run_id}"
            )

        # Prefijo por defecto
        if prefix is None:
            prefix = f'runs/{run_id}/prepared'

        results = []

        # Subir manifest.json
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

        # Subir archivos de medios por ad_id
        for ad_folder in prepared_dir.iterdir():
            if not ad_folder.is_dir():
                continue

            ad_id = ad_folder.name

            for media_file in ad_folder.iterdir():
                if not media_file.is_file():
                    continue

                blob_name = f'{prefix}/{ad_id}/{media_file.name}'

                try:
                    # Detectar content_type
                    ext = media_file.suffix.lower()
                    content_type_map = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.mp4': 'video/mp4',
                        '.webm': 'video/webm'
                    }
                    content_type = content_type_map.get(ext)

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

        # Resumen
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


@router.get("/runs/latest/gcs_manifest", tags=["Facebook"])
async def get_latest_run_gcs_manifest(
    expiration_hours: int = Query(
        24, ge=1, le=168,
        description="URL expiration in hours (1-168)"
    )
):
    """
    Obtiene automáticamente el último run_id y devuelve un manifest JSON
    con todas las URLs firmadas de GCS.

    Returns:
        {
            "run_id": "...",
            "created_at": "...",
            "url_expiration_hours": 24,
            "total_ads": 10,
            "total_files": 50,
            "ads": [...]
        }
    """
    try:
        # Obtener último run_id
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
        latest_run_id = run_dirs[0].name

        # Obtener archivos de GCS
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

        # Preparar manifest estructurado
        ads_manifest = []
        for ad_id, media_files in gcs_files['media_by_ad'].items():
            ads_manifest.append({
                'ad_id': ad_id,
                'media_count': len(media_files),
                'media_urls': [file['url'] for file in media_files]
            })

        # Fecha de creación
        created_at = run_dirs[0].stat().st_mtime
        created_datetime = datetime.fromtimestamp(
            created_at
        ).isoformat() + 'Z'

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
        description="Run ID (if None, uses latest)"
    ),
    expiration_hours: int = Query(
        24, ge=1, le=168,
        description="URL expiration in hours"
    ),
    output_filename: str = Query(
        "manifest.json",
        description="Output filename"
    )
):
    """
    Guarda el manifest de un run como archivo JSON local.

    Returns:
        {
            "status": "success",
            "run_id": "...",
            "manifest_path": "...",
            "manifest": {...}
        }
    """
    try:
        # Usar último run si no se especifica
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

        # Verificar run_dir
        saved_base = get_facebook_saved_base()
        run_dir = saved_base / run_id

        if not run_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Run directory not found: {run_id}"
            )

        # Obtener archivos de GCS
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

        # Preparar manifest
        ads_manifest = []
        for ad_id, media_files in gcs_files['media_by_ad'].items():
            ads_manifest.append({
                'ad_id': ad_id,
                'media_count': len(media_files),
                'media_urls': [file['url'] for file in media_files]
            })

        created_at = run_dir.stat().st_mtime
        created_datetime = datetime.fromtimestamp(
            created_at
        ).isoformat() + 'Z'

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

        # Guardar archivo
        manifest_path = run_dir / output_filename
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
