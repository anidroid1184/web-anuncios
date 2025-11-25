"""
Scraper routes - Endpoints para iniciar y ejecutar el scraper
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import asyncio

from ..facebook_actor import FacebookActor
from ..models.schemas import (
    FacebookScraperInput,
    SimpleScrapeRequest,
    FacebookStartResponse
)
from ..utils.config import get_facebook_saved_base
from app.processors.facebook.extract_dataset import fetch_and_store_run_dataset
from app.processors.facebook.analyze_dataset import analyze, analyze_jsonl
from app.processors.facebook.download_images_from_csv import (
    make_session,
    extract_urls_from_snapshot,
    iter_csv_snapshot_rows,
    download_one,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

router = APIRouter(tags=["Facebook"])


@router.post(
    "/scrape",
    response_model=FacebookStartResponse,
    status_code=202
)
async def scrape_facebook_ads(request: FacebookScraperInput):
    """
    Inicia el scraper de Facebook Ads Library de forma asíncrona.

    Retorna inmediatamente un run_id para consultar estado posteriormente.
    """
    try:
        actor = FacebookActor()
        actor_input = actor.build_actor_input(request)
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


@router.post("/scrape_and_save", status_code=200)
async def scrape_and_save(request: SimpleScrapeRequest):
    """
    Inicia el scraper, espera al resultado, guarda el dataset y genera
    automáticamente el manifest 'prepared' para análisis posterior.

    Returns:
        Metadata con run_id, dataset guardado, top ads y ruta del
        prepared_json generado.
    """
    try:
        actor = FacebookActor()

        # Construir input mínimo para el actor
        actor_input = {
            "count": int(request.count or 100),
            "scrapeAdDetails": True,
            "urls": [{"url": str(request.url)}],
        }

        # Iniciar actor asíncrono
        run_data = await asyncio.to_thread(actor.run_async, actor_input)

        if not run_data or not run_data.get("id"):
            raise HTTPException(
                status_code=500,
                detail="No se pudo iniciar el actor"
            )

        run_id = run_data.get("id")
        run_id_str = str(run_id)

        # Esperar hasta SUCCEEDED o timeout
        timeout = int(request.timeout or 600)
        poll_interval = 5
        elapsed = 0

        while elapsed < timeout:
            status_data = await asyncio.to_thread(
                actor.get_run_status, run_id_str
            )
            status = status_data.get("status") if status_data else None

            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "ABORTED"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Run finalizó con estado {status}"
                )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        if elapsed >= timeout:
            raise HTTPException(
                status_code=504,
                detail="Timeout esperando al run de Apify"
            )

        # Guardar dataset en disco
        if not run_id_str:
            raise HTTPException(status_code=500, detail="Run id inválido")

        meta = fetch_and_store_run_dataset(run_id_str)

        # Localizar CSV/JSONL generado
        run_dir = Path(str(meta.get("saved_jsonl", ""))).parent
        csv_path = run_dir / f"{run_id_str}.csv"

        # Construir stats
        stats = {}
        if csv_path.exists():
            stats = analyze(csv_path)
        else:
            jsonl_path = run_dir / f"{run_id_str}.jsonl"
            if jsonl_path.exists():
                stats = analyze_jsonl(jsonl_path)

        # Ordenar y tomar top 10
        items = sorted(
            stats.values(),
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        top_n = 10
        top_ads = [it.get("ad_id") for it in items[:top_n]]

        # Descargar medios de los top N anuncios
        media_dir = run_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        session = make_session()

        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = []

            if csv_path.exists():
                for row, snapshot in iter_csv_snapshot_rows(csv_path):
                    ad_id = (
                        row.get("ad_archive_id")
                        or row.get("ad_id")
                        or "unknown"
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
                                session,
                                u,
                                media_dir,
                                prefix=ad_id
                            )
                        )
            else:
                jsonl_path = run_dir / f"{run_id_str}.jsonl"
                if jsonl_path.exists():
                    with jsonl_path.open("r", encoding="utf-8") as jf:
                        for line in jf:
                            try:
                                item = json.loads(line)
                            except Exception:
                                continue
                            ad_id = (
                                item.get("ad_archive_id")
                                or item.get("adArchiveID")
                                or item.get("id")
                                or "unknown"
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
                                        session,
                                        u,
                                        media_dir,
                                        prefix=ad_id
                                    )
                                )

            downloaded = 0
            failures = 0
            for fut in as_completed(futures):
                url, path = fut.result()
                if path:
                    downloaded += 1
                else:
                    failures += 1

        # Intentar generar el manifest 'prepared' automáticamente
        prepared_json = None
        try:
            from .preparation import preparer_run
            preparer_result = await preparer_run(
                run_id=run_id_str,
                top=10,
                method='heuristic',
                max_dim=512,
                jpeg_quality=70,
                limit_per_ad=5,
                numeric_size=128,
                drive_folder_id=None,
            )
            if isinstance(preparer_result, dict):
                prepared_json = preparer_result.get('prepared_json')
        except Exception as e:
            print(f"Warning: Could not generate prepared_json: {e}")
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


@router.post("/download-dataset-from-run", status_code=200)
async def download_dataset_from_run(
    run_id: str,
    download_media: bool = True,
    download_limit: Optional[int] = None
):
    """
    Descarga el dataset de un run de Apify y lo guarda localmente.

    Este endpoint:
    1. Obtiene información del run desde Apify
    2. Descarga el dataset asociado (usando defaultDatasetId)
    3. Guarda CSV y JSONL localmente
    4. Descarga multimedia (imágenes y videos) si download_media=True
    5. Retorna metadata del dataset guardado

    Args:
        run_id: ID del run de Apify
        download_media: Si True, descarga imágenes y videos (default: True)
        download_limit: Límite de archivos multimedia a descargar (opcional)

    Returns:
        Metadata con información del dataset guardado, incluyendo conteo de multimedia descargada
    """
    try:
        # Descargar y guardar dataset con multimedia
        meta = await asyncio.to_thread(
            fetch_and_store_run_dataset,
            run_id,
            out_base=None,  # usa directorio por defecto
            download_media=download_media,
            download_limit=download_limit
        )

        if not meta:
            raise HTTPException(
                status_code=500,
                detail="No se pudo descargar el dataset"
            )

        response = {
            "status": "ok",
            "run_id": run_id,
            "dataset_id": meta.get("dataset_id"),
            "items_count": meta.get("items_count"),
            "saved_csv": meta.get("saved_csv"),
            "saved_jsonl": meta.get("saved_jsonl"),
        }

        # Agregar info de multimedia si se descargó
        if download_media:
            response["media_saved_count"] = meta.get("media_saved_count", 0)
            response["media_dir"] = meta.get("media_dir")

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error descargando dataset: {str(e)}"
        )
