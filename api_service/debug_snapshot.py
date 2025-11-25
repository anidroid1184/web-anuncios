"""
Script de diagnóstico para revisar el contenido del snapshot en el CSV
"""
import pandas as pd
import json
from pathlib import Path

# Configuración
run_id = "bfMXWLphPQcDmBsrz"
csv_path = Path(
    f"app/processors/datasets/saved_datasets/facebook/{run_id}/{run_id}.csv")

print("="*80)
print(f"🔍 DIAGNÓSTICO DE SNAPSHOT - {run_id}")
print("="*80)

if not csv_path.exists():
    print(f"❌ No se encontró el archivo: {csv_path}")
    exit(1)

# Leer CSV
df = pd.read_csv(csv_path)
print(f"\n✅ CSV cargado: {len(df)} filas")
print(f"📋 Columnas: {list(df.columns)}")

# Verificar columna snapshot
if 'snapshot' not in df.columns:
    print("\n❌ No existe columna 'snapshot' en el CSV")
    print(f"Columnas disponibles: {list(df.columns)}")
    exit(1)

print(f"\n✅ Columna 'snapshot' encontrada")

# Analizar primeros 3 anuncios
print("\n" + "="*80)
print("📊 ANÁLISIS DE LOS PRIMEROS 3 ANUNCIOS")
print("="*80)

for idx in range(min(3, len(df))):
    row = df.iloc[idx]
    ad_id = row.get('ad_archive_id') or row.get('ad_id') or 'unknown'

    print(f"\n--- ANUNCIO #{idx+1} (ID: {ad_id}) ---")

    snapshot_str = row.get('snapshot', '')

    if pd.isna(snapshot_str) or not snapshot_str:
        print("❌ Snapshot vacío o NaN")
        continue

    print(f"📄 Tipo de dato: {type(snapshot_str)}")
    print(f"📏 Longitud: {len(str(snapshot_str))} caracteres")
    print(f"🔤 Primeros 200 caracteres:")
    print(f"   {str(snapshot_str)[:200]}...")

    # Intentar parsear
    parsed = None
    parse_method = None

    # Método 1: JSON directo
    try:
        parsed = json.loads(snapshot_str)
        parse_method = "json.loads()"
    except:
        pass

    # Método 2: Reemplazar comillas simples
    if not parsed:
        try:
            parsed = json.loads(snapshot_str.replace("'", '"'))
            parse_method = "json.loads() con replace"
        except:
            pass

    # Método 3: eval()
    if not parsed:
        try:
            parsed = eval(snapshot_str)
            parse_method = "eval()"
        except:
            pass

    if parsed:
        print(f"✅ Parseado exitosamente con: {parse_method}")
        print(f"📦 Tipo resultante: {type(parsed)}")
        print(
            f"🔑 Claves principales: {list(parsed.keys()) if isinstance(parsed, dict) else 'No es dict'}")

        # Buscar imágenes
        if isinstance(parsed, dict):
            if 'images' in parsed:
                images = parsed['images']
                print(f"   📸 images: {len(images)} elemento(s)")
                if images and isinstance(images, list):
                    first_img = images[0]
                    print(
                        f"      Claves primer elemento: {list(first_img.keys()) if isinstance(first_img, dict) else type(first_img)}")
            else:
                print(f"   ⚠️  NO tiene clave 'images'")

            if 'videos' in parsed:
                videos = parsed['videos']
                print(f"   🎥 videos: {len(videos)} elemento(s)")
                if videos and isinstance(videos, list):
                    first_vid = videos[0]
                    print(
                        f"      Claves primer elemento: {list(first_vid.keys()) if isinstance(first_vid, dict) else type(first_vid)}")
            else:
                print(f"   ⚠️  NO tiene clave 'videos'")
    else:
        print(f"❌ NO se pudo parsear con ningún método")
        print(f"   Intentar parsear manualmente estos datos")

# Estadísticas generales
print("\n" + "="*80)
print("📊 ESTADÍSTICAS GENERALES")
print("="*80)

total_with_snapshot = df['snapshot'].notna().sum()
total_empty_snapshot = df['snapshot'].isna().sum()

print(f"Total anuncios: {len(df)}")
print(f"Con snapshot: {total_with_snapshot}")
print(f"Sin snapshot: {total_empty_snapshot}")

# Contar videos
videos_count = 0
images_count = 0
parse_errors = 0

for _, row in df.iterrows():
    snapshot_str = row.get('snapshot', '')
    if pd.isna(snapshot_str) or not snapshot_str:
        continue

    try:
        # Intentar parsear
        try:
            snapshot = json.loads(snapshot_str)
        except:
            try:
                snapshot = json.loads(snapshot_str.replace("'", '"'))
            except:
                snapshot = eval(snapshot_str)

        if isinstance(snapshot, dict):
            if 'videos' in snapshot and snapshot['videos']:
                videos_count += 1
            if 'images' in snapshot and snapshot['images']:
                images_count += 1
    except:
        parse_errors += 1

print(f"\n📊 Contenido:")
print(f"   Anuncios con videos: {videos_count}")
print(f"   Anuncios con imágenes: {images_count}")
print(f"   Errores de parseo: {parse_errors}")

print("\n" + "="*80)
print("✅ DIAGNÓSTICO COMPLETO")
print("="*80)
