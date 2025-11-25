"""
Módulo de Workflows - End-to-end automation workflows
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import asyncio
from .utils import get_facebook_saved_base

router = APIRouter()

# Referencias a servicios (serán inicializadas desde el módulo principal)
actor_facebook = None
gcs_service = None


def init_workflow_dependencies(facebook_actor, gcs_svc):
    """Inicializa las dependencias del workflow"""
    global actor_facebook, gcs_service
    actor_facebook = facebook_actor
    gcs_service = gcs_svc


@router.post('/scrape_prepare_upload_gcs', tags=["workflows"])
async def scrape_prepare_and_upload_to_gcs(
    url: str = Query(..., description="Facebook Ads Library URL"),
    count: int = Query(10, ge=1, le=100, description="Number of ads"),
    top: int = Query(10, ge=1, le=50, description="Top N ads to prepare"),
    limit_per_ad: int = Query(
        5, ge=1, le=20,
        description="Max media files per ad"
    ),
    bucket_name: Optional[str] = None,
    prefix: Optional[str] = None,
    timeout: int = Query(
        300, ge=10, le=3600,
        description="Scraper timeout in seconds"
    )
):
    """
    Workflow completo end-to-end:
    1. Scrape Facebook Ads Library
    2. Download dataset
    3. Analyze and download top N ads media
    4. Prepare files (resize, convert)
    5. Upload to GCS
    6. Generate manifest with signed URLs

    Returns complete execution report with GCS URLs.
    """
    try:
        if actor_facebook is None:
            raise HTTPException(
                status_code=503,
                detail="Facebook Actor not configured"
            )
        if gcs_service is None:
            raise HTTPException(
                status_code=503,
                detail="GCS service not configured"
            )

        # Import necessary functions
        from app.processors.facebook.extract_dataset import (
            fetch_and_store_run_dataset
        )
        from app.processors.facebook.analyze_dataset import (
            analyze, analyze_jsonl
        )
        from app.processors.facebook.download_images_from_csv import (
            iter_csv_snapshot_rows,
            extract_urls_from_snapshot,
            download_one,
            make_session
        )

        # PASO 1: Iniciar scraper
        actor_input = {
            "resultsLimit": count,
            "scrapeAdDetails": True,
            "urls": [{"url": url}],
        }

        run_data = await asyncio.to_thread(
            actor_facebook.run_async,
            actor_input
        )

        if not run_data or not run_data.get("id"):
            raise HTTPException(
                status_code=500,
                detail="Failed to start Facebook scraper"
            )

        run_id = str(run_data.get("id"))

        # PASO 2: Esperar a que termine
        poll_interval = 5
        elapsed = 0

        while elapsed < timeout:
            status_data = await asyncio.to_thread(
                actor_facebook.get_run_status,
                run_id
            )
            status = status_data.get("status") if status_data else None

            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "ABORTED"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Scraper failed with status: {status}"
                )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        if elapsed >= timeout:
            raise HTTPException(
                status_code=504,
                detail=f"Scraper timeout ({timeout}s)"
            )

        # PASO 3: Descargar y guardar dataset
        meta = fetch_and_store_run_dataset(run_id)

        # PASO 4: Analizar y descargar media de top-N
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
                detail='Dataset file not found'
            )

        items = sorted(
            stats.values(),
            key=lambda x: x.get('score', 0),
            reverse=True
        )
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
                    ad_id = (
                        row.get("ad_archive_id") or
                        row.get("ad_id") or
                        "unknown"
                    )
                    if ad_id not in top_ads:
                        continue
                    if not snapshot:
                        continue
                    urls = extract_urls_from_snapshot(snapshot)
                    for u in urls:
                        futures.append(
                            ex.submit(
                                download_one,
                                session, u, media_dir,
                                prefix=ad_id
                            )
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
                                ex.submit(
                                    download_one,
                                    session, u, media_dir,
                                    prefix=ad_id
                                )
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
        # Importar preparer desde el mismo módulo facebook
        from ..facebook_routes import preparer_run

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
        from .gcs import upload_prepared_to_gcs, get_run_gcs_files

        upload_result = await upload_prepared_to_gcs(
            run_id=run_id,
            bucket_name=bucket_name,
            prefix=prefix
        )

        # PASO 7: Obtener URLs firmadas
        gcs_files = await get_run_gcs_files(
            run_id=run_id,
            generate_signed_urls=True,
            expiration_hours=24
        )

        return {
            'status': 'success',
            'message': 'Complete workflow executed successfully',
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
            'bucket_url': (
                f"https://console.cloud.google.com/storage/browser/"
                f"{bucket_name or gcs_service.default_bucket_name}/"
                f"runs/{run_id}/prepared/"
            )
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
