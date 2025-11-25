"""Extractor de datasets desde Apify para Facebook Ads Library.

Guarda items del dataset del run en
`datasets/facebook/<run_id>/` en JSONL y, si pandas está disponible, en CSV.

Uso:
    python extract_dataset.py --run-id yanjWofg2yllX3R9A

Requiere:
    - APIFY_TOKEN en las variables de entorno
    - apify-client instalado
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Generator, Dict, Any, Optional
import argparse
import requests
from urllib.parse import urlparse

try:
    from apify_client import ApifyClient
except Exception:  # pragma: no cover - library missing
    raise


def get_apify_client() -> ApifyClient:
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_TOKEN not set in environment")
    return ApifyClient(token)


def get_dataset_id_for_run(client: ApifyClient, run_id: str) -> Optional[str]:
    run = client.run(run_id).get()
    if not run:
        return None
    return run.get("defaultDatasetId")


def iterate_dataset_items(
    client: ApifyClient,
    dataset_id: str,
    limit: int = 1000,
) -> Generator[Dict[str, Any], None, None]:
    """Itera todos los items del dataset usando paginación.

    Args:
        client: ApifyClient
        dataset_id: id del dataset (ej: "dataset/xxxxx")
        limit: tamaño de página
    """
    dataset_client = client.dataset(dataset_id)
    offset = 0
    while True:
        resp = dataset_client.list_items(limit=limit, offset=offset)
        items = getattr(resp, "items", None)
        if not items:
            break
        for it in items:
            yield it
        if len(items) < limit:
            break
        offset += limit


def save_items_jsonl(
    items_gen: Generator[Dict[str, Any], None, None],
    out_path: Path,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8") as f:
        for it in items_gen:
            f.write(json.dumps(it, ensure_ascii=False))
            f.write("\n")
            count += 1
    return count


def try_save_csv(jsonl_path: Path, csv_path: Path) -> bool:
    try:
        import pandas as pd
    except Exception:
        return False
    # leer JSONL en DataFrame y guardar
    df = pd.read_json(jsonl_path, lines=True)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    return True


def sanitize_filename_from_url(url: str, prefix: str = "") -> str:
    """Crea un nombre de archivo seguro a partir de una URL."""
    p = urlparse(url)
    basename = os.path.basename(p.path) or "file"
    name = f"{prefix}_{basename}" if prefix else basename
    # truncar a longitud razonable
    return name[:180]


def download_file(url: str, dest_path: Path, timeout: int = 20) -> bool:
    """Descarga un archivo en streaming a dest_path."""
    try:
        r = requests.get(url, stream=True, timeout=timeout)
        r.raise_for_status()
        with dest_path.open("wb") as f:
            for chunk in r.iter_content(1024 * 16):
                if chunk:
                    f.write(chunk)
        return True
    except Exception:
        return False


def fetch_and_store_run_dataset(
    run_id: str,
    out_base: Optional[Path] = None,
    download_media: bool = False,
    download_limit: Optional[int] = None,
) -> Dict[str, Any]:
    client = get_apify_client()
    ds_id = get_dataset_id_for_run(client, run_id)
    if not ds_id:
        raise RuntimeError(f"No dataset associated with run {run_id}")

    if out_base is None:
        # Save into the `saved_datasets/facebook` folder by default.
        out_base = (
            Path(__file__).parent.parent
            / "datasets"
            / "saved_datasets"
            / "facebook"
        )
    else:
        out_base = Path(out_base)

    run_dir = out_base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = run_dir / f"{run_id}.jsonl"
    csv_path = run_dir / f"{run_id}.csv"

    items_gen = iterate_dataset_items(client, ds_id)
    count = save_items_jsonl(items_gen, jsonl_path)

    csv_ok = try_save_csv(jsonl_path, csv_path)
    # preparar metadata básica
    meta = {
        "run_id": run_id,
        "dataset_id": ds_id,
        "saved_jsonl": str(jsonl_path),
        "saved_csv": str(csv_path) if csv_ok else None,
        "items_count": count,
    }

    # si se solicitó, extraer URLs de medios y descargarlos
    if download_media:
        media_dir = run_dir / "media"
        media_dir.mkdir(exist_ok=True)
        # leer JSONL y extraer urls
        media_rows = []
        with jsonl_path.open("r", encoding="utf-8") as jf:
            for line in jf:
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                # extraer media del item
                snap = item.get("snapshot") or {}
                # snapshot.images
                for im in snap.get("images") or []:
                    url = (
                        im.get("original_image_url")
                        or im.get("image_url")
                        or im.get("url")
                    )
                    if url:
                        adid = (
                            item.get("ad_archive_id")
                            or item.get("adArchiveID")
                            or item.get("id")
                        )
                        media_rows.append(("image", adid, url))
                # snapshot.cards
                for c in snap.get("cards") or []:
                    url = (
                        c.get("original_image_url")
                        or c.get("image_url")
                        or c.get("url")
                    )
                    if url:
                        adid = (
                            item.get("ad_archive_id")
                            or item.get("adArchiveID")
                            or item.get("id")
                        )
                        media_rows.append(("image", adid, url))
                # snapshot.videos
                for v in snap.get("videos") or []:
                    url = (
                        v.get("video_sd_url")
                        or v.get("video_url")
                        or v.get("url")
                    )
                    if url:
                        adid = (
                            item.get("ad_archive_id")
                            or item.get("adArchiveID")
                            or item.get("id")
                        )
                        media_rows.append(("video", adid, url))
                # revisar keys planas que algunos scrapers usan
                for key in (
                    "snapshot.images",
                    "snapshot.cards",
                    "snapshot.videos",
                ):
                    val = item.get(key)
                    if val and isinstance(val, list):
                        for el in val:
                            if isinstance(el, dict):
                                maybe = (
                                    el.get("original_image_url")
                                    or el.get("url")
                                    or el.get("image_url")
                                )
                                if maybe:
                                    adid = (
                                        item.get("ad_archive_id")
                                        or item.get("adArchiveID")
                                        or item.get("id")
                                    )
                                    media_rows.append(("image", adid, maybe))
                            elif isinstance(el, str):
                                adid = (
                                    item.get("ad_archive_id")
                                    or item.get("adArchiveID")
                                    or item.get("id")
                                )
                                media_rows.append(("image", adid, el))

        # descargar medios (opcionalmente limitado)
        downloaded = 0
        for typ, ad_id, url in media_rows:
            if download_limit is not None and downloaded >= download_limit:
                break
            # construir nombre de archivo seguro
            fname = sanitize_filename_from_url(url, prefix=str(ad_id or "ad"))
            dest = media_dir / fname
            if dest.exists():
                downloaded += 1
                continue
            ok = download_file(url, dest)
            if ok:
                downloaded += 1

        meta["media_saved_count"] = downloaded
        meta["media_dir"] = str(media_dir)
    # guardar metadata
    with (run_dir / "metadata.json").open("w", encoding="utf-8") as mf:
        json.dump(meta, mf, ensure_ascii=False, indent=2)

    return meta


def main():
    p = argparse.ArgumentParser(
        description=(
            "Fetch Apify dataset for a Facebook run and store locally"
        )
    )
    p.add_argument("--run-id", required=True)
    p.add_argument("--out", required=False, help="Base output dir (optional)")
    args = p.parse_args()

    run_id = args.run_id
    out_base = Path(args.out) if args.out else None

    meta = fetch_and_store_run_dataset(run_id, out_base=out_base)
    print("Done:", meta)


if __name__ == "__main__":
    main()
