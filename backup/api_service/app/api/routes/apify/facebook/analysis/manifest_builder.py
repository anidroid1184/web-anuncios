"""
Manifest Builder Module
Construye manifests desde archivos en GCS
"""
from typing import Dict, Any
from fastapi import HTTPException


def build_manifest_from_gcs(
    run_id: str,
    gcs_service: Any
) -> Dict[str, Any]:
    """
    Construye un manifest desde archivos en GCS bucket

    Args:
        run_id: ID del run a buscar en GCS
        gcs_service: Instancia del servicio GCS

    Returns:
        Dict con run_id y lista de ads con sus archivos

    Raises:
        HTTPException: Si no se encuentran archivos o hay error
    """
    # Construir prefix del run en GCS
    bucket_name = gcs_service.default_bucket_name
    prefix = f'runs/{run_id}/prepared/'

    # Listar archivos en GCS
    try:
        blobs = gcs_service.list_blobs(
            prefix=prefix,
            bucket_name=bucket_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No files found in bucket for run_id "
                f"{run_id}: {str(e)}"
            )
        )

    if not blobs:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No files found for run_id {run_id} "
                f"in bucket {bucket_name}"
            )
        )

    # Organizar archivos por ad_id
    media_by_ad = {}

    for blob_info in blobs:
        blob_name = blob_info['name']

        # Saltar manifests JSON
        if 'manifest.json' in blob_name or blob_name.endswith('.json'):
            continue

        # Extraer ad_id del path: runs/{run_id}/prepared/{ad_id}/{file}
        parts = blob_name.split('/')
        if len(parts) >= 4:
            ad_id = parts[3]
            if ad_id not in media_by_ad:
                media_by_ad[ad_id] = []

            # Determinar tipo de archivo
            lower = blob_name.lower()
            if lower.endswith('.mp4') or 'video' in lower:
                ftype = 'video'
            elif any(
                lower.endswith(ext)
                for ext in ['.jpg', '.jpeg', '.png']
            ):
                ftype = 'image'
            else:
                ftype = 'unknown'

            media_by_ad[ad_id].append({
                'url': blob_info['public_url'],
                'type': ftype,
                'blob_name': blob_name
            })

    # Construir manifest
    manifest_data = {'run_id': run_id, 'ads': []}
    for ad_id, files in media_by_ad.items():
        manifest_data['ads'].append({
            'ad_id': ad_id,
            'files': files
        })

    if not manifest_data['ads']:
        raise HTTPException(
            status_code=404,
            detail=f"No media files found for run_id {run_id}"
        )

    return manifest_data
