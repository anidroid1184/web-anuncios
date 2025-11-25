"""
Módulo orquestador para construir el dataset completo
Coordina: fetch → transform → download → persist
"""
from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
import json
import pandas as pd
from tqdm import tqdm

from .schema import infer_item_id
from .transform import normalize_item, filter_valid_items
from .media import bulk_download


def build_from_items(
    items: List[Dict[str, Any]],
    out_dir: Path,
    img_dir: Path,
    prefer_cover: bool = True,
    max_workers: int = 16,
    download_images: bool = True
) -> None:
    """
    Construye el dataset completo a partir de items raw de Apify

    Proceso:
    1. Filtrar items válidos
    2. Normalizar items y calcular métricas
    3. Descargar imágenes (opcional)
    4. Crear label de viralidad
    5. Persistir: parquet, csv, jsonl

    Args:
        items: Lista de items raw desde Apify
        out_dir: Directorio de salida
        img_dir: Directorio para imágenes
        prefer_cover: Si True, prioriza cover sobre avatar en manifest
        max_workers: Workers para descarga paralela
        download_images: Si False, omite descarga de imágenes

    Outputs:
        - metadata.parquet: Todos los datos normalizados
        - labels.csv: ID, paths, métricas y labels
        - manifest.jsonl: Formato para ML (una línea por item)
    """
    print(f"📊 Construyendo dataset desde {len(items)} items...")

    # Crear directorios
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    # 1. Filtrar items válidos
    print("🔍 Filtrando items válidos...")
    valid_items = filter_valid_items(items)
    print(f"   ✓ {len(valid_items)} items válidos de {len(items)}")

    # 2. Normalizar items
    print("🔄 Normalizando items...")
    rows: List[Dict[str, Any]] = []
    for idx, it in enumerate(tqdm(valid_items, desc="Normalizando")):
        item_id = infer_item_id(it, str(idx))
        rows.append(normalize_item(it, item_id))

    # 3. Descargar imágenes
    if download_images:
        print("🖼️  Descargando imágenes...")
        rows = bulk_download(rows, img_dir, max_workers=max_workers)
    else:
        print("⏭️  Omitiendo descarga de imágenes")
        # Agregar columnas vacías
        for row in rows:
            row["avatar_path"] = None
            row["cover_path"] = None

    # 4. Crear DataFrame
    print("📋 Creando DataFrame...")
    df = pd.DataFrame(rows)

    # 5. Calcular label de viralidad (percentil 75 de ER)
    print("🏷️  Calculando labels de viralidad...")
    if df["ER_play"].notna().sum() > 0:
        threshold = df["ER_play"].quantile(0.75)
        df["label_viral"] = (df["ER_play"] >= threshold).astype("Int64")
        print(f"   ✓ Threshold: {threshold:.4f}")
    else:
        df["label_viral"] = pd.NA
        print("   ⚠️  No hay suficientes datos para calcular viralidad")

    # 6. Persistir metadata.parquet
    print("💾 Guardando metadata.parquet...")
    metadata_path = out_dir / "metadata.parquet"
    df.to_parquet(metadata_path, index=False)
    print(f"   ✓ {metadata_path}")

    # 7. Persistir labels.csv
    print("💾 Guardando labels.csv...")
    labels_cols = [
        "id",
        "cover_path",
        "avatar_path",
        "ER_play",
        "total_engagement",
        "label_viral"
    ]
    labels_path = out_dir / "labels.csv"
    df[labels_cols].to_csv(labels_path, index=False)
    print(f"   ✓ {labels_path}")

    # 8. Persistir manifest.jsonl
    print("💾 Guardando manifest.jsonl...")
    manifest_path = out_dir / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as f:
        for r in tqdm(
            df.to_dict(orient="records"),
            desc="Escribiendo manifest"
        ):
            # Determinar imagen preferida
            if prefer_cover:
                image = r.get("cover_path") or r.get("avatar_path")
            else:
                image = r.get("avatar_path") or r.get("cover_path")

            # Construir objeto para manifest
            obj = {
                "id": r["id"],
                "image": image,
                "caption": r.get("text"),
                "duration_s": r.get("duration_s"),
                "playCount": r.get("playCount"),
                "diggCount": r.get("diggCount"),
                "shareCount": r.get("shareCount"),
                "commentCount": r.get("commentCount"),
                "collectCount": r.get("collectCount"),
                "ER_play": r.get("ER_play"),
                "total_engagement": r.get("total_engagement"),
                "label_viral": r.get("label_viral"),
                "webVideoUrl": r.get("webVideoUrl"),
                "hashtags": r.get("hashtags"),
                "n_hashtags": r.get("n_hashtags"),
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"   ✓ {manifest_path}")

    # 9. Estadísticas finales
    print("\n" + "="*60)
    print("✅ Dataset construido exitosamente!")
    print("="*60)
    print(f"📊 Total de items: {len(df)}")
    print(f"🖼️  Imágenes descargadas: {df['cover_path'].notna().sum()}")
    print(f"🔥 Items virales: {df['label_viral'].sum()}")
    print(f"📁 Directorio de salida: {out_dir}")
    print("="*60)


def build_from_json(
    json_path: Path,
    out_dir: Path,
    img_dir: Path,
    **kwargs
) -> None:
    """
    Construye dataset desde un archivo JSON de items

    Args:
        json_path: Path al archivo JSON con items
        out_dir: Directorio de salida
        img_dir: Directorio para imágenes
        **kwargs: Argumentos adicionales para build_from_items
    """
    print(f"📂 Cargando items desde {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    build_from_items(items, out_dir, img_dir, **kwargs)


def get_dataset_stats(out_dir: Path) -> Dict[str, Any]:
    """
    Obtiene estadísticas del dataset construido

    Args:
        out_dir: Directorio del dataset

    Returns:
        Diccionario con estadísticas
    """
    metadata_path = out_dir / "metadata.parquet"

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"No se encontró metadata.parquet en {out_dir}"
        )

    df = pd.read_parquet(metadata_path)

    return {
        "total_items": len(df),
        "date_range": {
            "earliest": df["createTimeISO"].min(),
            "latest": df["createTimeISO"].max()
        },
        "engagement": {
            "avg_er": df["ER_play"].mean(),
            "median_er": df["ER_play"].median(),
            "total_plays": df["playCount"].sum(),
            "total_likes": df["diggCount"].sum()
        },
        "content": {
            "unique_authors": df["author_name"].nunique(),
            "avg_duration": df["duration_s"].mean(),
            "with_music": df["has_music"].sum(),
            "original_music": df["is_original_music"].sum()
        },
        "viral_items": int(df["label_viral"].sum()),
        "images_downloaded": int(df["cover_path"].notna().sum())
    }
