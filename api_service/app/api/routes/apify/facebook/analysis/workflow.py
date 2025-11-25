"""
Workflow Module
Orquesta el flujo completo: scraping, preparación y subida a GCS
"""
import asyncio
import shutil
from typing import Dict, Any
from fastapi import HTTPException
import logging

# Configurar logger
logger = logging.getLogger(__name__)


async def scrape_and_prepare_run(
    url: str,
    count: int = 100,
    top: int = 10
) -> Dict[str, Any]:
    """
    Ejecuta scraping, preparación y subida a GCS
    Reutiliza endpoints existentes

    Args:
        url: URL de Facebook Ads Library
        count: Cantidad de anuncios a scrapear
        top: Top N anuncios a procesar

    Returns:
        Dict con run_id, manifest y estadísticas
    """
    logger.info("="*70)
    logger.info("🔄 WORKFLOW: Iniciando scrape_and_prepare_run")
    logger.info("="*70)

    from ..facebook_actor import FacebookActor
    from app.processors.facebook.analyze_dataset import (
        analyze,
        analyze_jsonl
    )
    from app.processors.facebook.download_images_from_csv import (
        iter_csv_snapshot_rows,
        extract_urls_from_snapshot,
        download_one,
        make_session
    )
    from ..utils.config import get_facebook_saved_base, get_gcs_service

    logger.info("📦 Paso 1/8: Inicializando Facebook Actor...")
    actor = FacebookActor()
    logger.info("   ✅ Actor inicializado")

    # 1. Scrape
    logger.info("\n🌐 Paso 2/8: Iniciando scraping en Apify...")
    logger.info(f"   - URL: {url[:80]}...")
    logger.info(f"   - Results limit: {count}")

    actor_input = {
        "count": int(count),
        "scrapeAdDetails": True,
        "urls": [{"url": url}],
    }

    try:
        run_data = await asyncio.to_thread(actor.run_async, actor_input)
    except Exception as e:
        logger.error(f"   ❌ Error ejecutando actor: {str(e)}")
        logger.error(f"   ❌ Tipo de error: {type(e).__name__}")
        import traceback
        logger.error(f"   ❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error starting actor: {type(e).__name__}: {str(e)}"
        )

    if not run_data or not run_data.get("id"):
        logger.error("   ❌ Actor no retornó run_id")
        raise HTTPException(
            status_code=500,
            detail="Failed to start scraper"
        )

    run_id = str(run_data.get("id"))
    logger.info(f"   ✅ Scraping iniciado - Run ID: {run_id}")

    # 2. Wait for completion
    logger.info("\n⏳ Paso 3/8: Esperando finalización del scraping...")
    timeout = 600  # 10 minutos (era 5 minutos)
    poll_interval = 5
    elapsed = 0
    logger.info(
        f"   - Timeout configurado: {timeout}s ({timeout//60} minutos)")

    while elapsed < timeout:
        status_data = await asyncio.to_thread(
            actor.get_run_status,
            run_id
        )
        if not status_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to get run status"
            )
        status = status_data.get("status")

        if status == "SUCCEEDED":
            logger.info(f"   ✅ Scraping completado (tiempo: {elapsed}s)")
            break
        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
            logger.error(f"   ❌ Scraper falló con status: {status}")
            raise HTTPException(
                status_code=500,
                detail=f"Scraper failed with status: {status}"
            )

        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    if elapsed >= timeout:
        logger.error("   ❌ Timeout esperando scraper")
        raise HTTPException(
            status_code=504,
            detail="Scraper timeout"
        )

    # 3. Download dataset
    logger.info("\n💾 Paso 4/8: Descargando dataset desde Apify...")

    from app.processors.facebook.extract_dataset import (
        fetch_and_store_run_dataset
    )

    try:
        # Llamar igual que scrape_and_save - sin out_base
        dataset_result = await asyncio.to_thread(
            fetch_and_store_run_dataset,
            run_id
        )
        logger.info("   ✅ Dataset descargado")
        items_count = dataset_result.get('items_count', 0)
        logger.info(f"   ✅ Items guardados: {items_count}")
        dataset_id = dataset_result.get('dataset_id', 'N/A')
        logger.info(f"   ✅ Dataset ID: {dataset_id}")
    except Exception as e:
        logger.error(f"   ❌ Error descargando dataset: {str(e)}")
        raise

    # Validar que se guardaron archivos
    if not dataset_result or not dataset_result.get("items_count"):
        logger.error("   ❌ No se guardaron items en el dataset")
        raise HTTPException(
            status_code=500,
            detail="Failed to download dataset: no items saved"
        )

    # Obtener directorio igual que scrape_and_save
    from pathlib import Path
    run_dir = Path(str(dataset_result.get("saved_jsonl", ""))).parent

    # 4. Analyze and get top ads
    logger.info(f"\n📊 Paso 5/8: Analizando dataset para obtener top {top}...")
    csv_path = run_dir / f'{run_id}.csv'
    jsonl_path = run_dir / f'{run_id}.jsonl'

    logger.info(f"   - Buscando CSV: {csv_path.name}")
    logger.info(f"   - Buscando JSONL: {jsonl_path.name}")

    try:
        if csv_path.exists():
            logger.info(
                f"   ✅ Archivo CSV encontrado ({csv_path.stat().st_size} bytes)")
            stats = analyze(csv_path, method='heuristic')
            logger.info(f"   ✅ Análisis completado - {len(stats)} anuncios")
        elif jsonl_path.exists():
            logger.info(
                f"   ✅ Archivo JSONL encontrado ({jsonl_path.stat().st_size} bytes)")
            stats = analyze_jsonl(jsonl_path, method='heuristic')
            logger.info(f"   ✅ Análisis completado - {len(stats)} anuncios")
        else:
            logger.error("   ❌ No se encontró CSV ni JSONL")
            logger.error(
                f"   Archivos en {run_dir}: {list(run_dir.iterdir())}")
            raise HTTPException(
                status_code=404,
                detail="No dataset found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ Error analizando dataset: {str(e)}")
        raise

    items = sorted(
        stats.values(),
        key=lambda x: x.get('score', 0),
        reverse=True
    )
    top_items = items[:top]
    top_ads = [it.get('ad_id') for it in top_items]
    logger.info(f"   ✅ Top {len(top_ads)} anuncios seleccionados")

    # 5. Download media files
    logger.info("\n📥 Paso 6/8: Descargando archivos multimedia...")
    media_dir = run_dir / 'media'

    try:
        media_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"   - Directorio media: {media_dir}")
    except Exception as e:
        logger.error(f"   ❌ Error creando directorio media: {str(e)}")
        raise

    session = make_session()
    downloaded_count = 0

    if csv_path.exists():
        logger.info("   - Procesando CSV para extraer URLs...")
        for row_dict, parsed_snapshot in iter_csv_snapshot_rows(csv_path):
            ad_id = row_dict.get('ad_archive_id') or row_dict.get('id')
            if ad_id not in top_ads:
                continue

            urls = extract_urls_from_snapshot(parsed_snapshot)
            for media_url in urls[:5]:  # max 5 per ad
                try:
                    download_one(
                        session,
                        media_url,
                        media_dir,
                        prefix=ad_id
                    )
                    downloaded_count += 1
                except Exception as e:
                    logger.debug(
                        f"   Advertencia: Error descargando {media_url[:50]}... : {str(e)}")
                    continue

        logger.info(f"   ✅ {downloaded_count} archivos multimedia descargados")
    else:
        logger.warning(
            "   ⚠️  CSV no disponible, saltando descarga multimedia")

    # 6. Prepare files (copy to prepared/)
    logger.info("\n📂 Paso 7/8: Preparando archivos para upload...")
    prepared_dir = run_dir / 'prepared'

    try:
        prepared_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"   - Directorio prepared: {prepared_dir}")
    except Exception as e:
        logger.error(f"   ❌ Error creando directorio prepared: {str(e)}")
        raise

    files_prepared = 0
    for ad_id in top_ads:
        ad_prepared_dir = prepared_dir / str(ad_id)
        ad_prepared_dir.mkdir(parents=True, exist_ok=True)

        matched = [
            p for p in media_dir.iterdir()
            if p.is_file() and p.name.startswith(str(ad_id or ''))
        ]

        for p in matched[:5]:
            try:
                shutil.copy2(p, ad_prepared_dir / p.name)
                files_prepared += 1
            except Exception as e:
                logger.debug(f"   Error copiando {p.name}: {str(e)}")
                continue

    logger.info(f"   ✅ {files_prepared} archivos preparados")

    # 7. Upload to GCS
    logger.info("\n☁️  Paso 8/8: Subiendo archivos a Google Cloud Storage...")
    gcs_service = get_gcs_service()
    if gcs_service is None:
        logger.error("   ❌ GCS service no configurado")
        raise HTTPException(
            status_code=503,
            detail="GCS service not configured"
        )

    bucket_name = gcs_service.default_bucket_name
    prefix = f'runs/{run_id}/prepared/'
    logger.info(f"   - Bucket: {bucket_name}")
    logger.info(f"   - Prefix: {prefix}")

    uploaded_files = []
    upload_errors = 0

    for file_path in prepared_dir.rglob('*'):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(prepared_dir)
        blob_name = f'{prefix}{relative_path}'.replace('\\', '/')

        try:
            result = gcs_service.upload_file(
                local_path=str(file_path),
                blob_name=blob_name,
                bucket_name=bucket_name
            )
            uploaded_files.append({
                'blob_name': blob_name,
                'public_url': result['public_url'],
                'ad_id': file_path.parent.name
            })
        except Exception as e:
            upload_errors += 1
            logger.debug(f"   Error subiendo {blob_name}: {str(e)}")
            continue

    logger.info(f"   ✅ {len(uploaded_files)} archivos subidos")
    if upload_errors > 0:
        logger.warning(f"   ⚠️  {upload_errors} archivos fallaron")

    # 8. Build manifest
    logger.info("\n📋 Construyendo manifest...")
    manifest = {'run_id': run_id, 'ads': []}
    media_by_ad = {}

    for file_info in uploaded_files:
        ad_id = file_info['ad_id']
        if ad_id not in media_by_ad:
            media_by_ad[ad_id] = []

        is_video = file_info['blob_name'].endswith('.mp4')
        file_type = 'video' if is_video else 'image'
        media_by_ad[ad_id].append({
            'url': file_info['public_url'],
            'type': file_type
        })

    for ad_id, files in media_by_ad.items():
        manifest['ads'].append({
            'ad_id': ad_id,
            'files': files
        })

    logger.info(f"   ✅ Manifest creado con {len(manifest['ads'])} anuncios")
    logger.info("="*70)
    logger.info("✨ WORKFLOW COMPLETADO EXITOSAMENTE")
    logger.info("="*70)

    return {
        'run_id': run_id,
        'manifest': manifest,
        'uploaded_files': len(uploaded_files),
        'top_ads': len(top_ads)
    }
