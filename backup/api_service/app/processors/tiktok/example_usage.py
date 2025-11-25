"""
Script de ejemplo: Construir dataset de TikTok desde un run de Apify
Uso: python -m app.processors.tiktok.example_usage
"""
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from app.processors.tiktok import (  # noqa: E402
    fetch_items_from_run,
    build_from_items,
    get_dataset_stats,
    SETTINGS
)


def main():
    """Ejemplo completo de uso del paquete de TikTok datasets"""

    print("="*60)
    print("🎵 TikTok Dataset Builder - Ejemplo de Uso")
    print("="*60)

    # 1. Verificar token
    if not SETTINGS.apify_token:
        print("❌ Error: APIFY_TOKEN no configurado en .env")
        return

    print("✅ Token configurado")
    print(f"📁 Directorio de salida: {SETTINGS.out_dir}")

    # 2. Solicitar run_id al usuario
    run_id = input("\n🔑 Ingresa el Run ID de Apify: ").strip()
    if not run_id:
        print("❌ Run ID requerido")
        return

    try:
        # 3. Asegurar directorios
        print("\n📂 Creando directorios...")
        SETTINGS.ensure_directories()

        # 4. Descargar items
        print(f"\n⬇️  Descargando items del run {run_id}...")
        items = fetch_items_from_run(
            token=SETTINGS.apify_token,
            run_id=run_id,
            page_size=SETTINGS.page_size
        )

        print(f"✅ {len(items)} items descargados\n")

        # 5. Preguntar si descargar imágenes
        download_images = input(
            "🖼️  ¿Descargar imágenes? (S/n): "
        ).strip().lower() != 'n'

        # 6. Construir dataset
        print("\n🔨 Construyendo dataset...")
        build_from_items(
            items=items,
            out_dir=SETTINGS.out_dir,
            img_dir=SETTINGS.images_dir(),
            max_workers=SETTINGS.max_workers,
            download_images=download_images
        )

        # 7. Mostrar estadísticas
        print("\n📊 Obteniendo estadísticas...")
        stats = get_dataset_stats(SETTINGS.out_dir)

        print("\n" + "="*60)
        print("📈 ESTADÍSTICAS DEL DATASET")
        print("="*60)
        print(f"Total de items: {stats['total_items']:,}")
        print(f"Items virales: {stats['viral_items']:,}")
        print(f"Autores únicos: {stats['content']['unique_authors']:,}")
        print(f"ER promedio: {stats['engagement']['avg_er']:.4f}")
        print(f"ER mediana: {stats['engagement']['median_er']:.4f}")
        print(f"Imágenes descargadas: {stats['images_downloaded']:,}")
        print("="*60)

        print("\n✅ Proceso completado!")
        print(f"\n📂 Archivos generados en: {SETTINGS.out_dir}")
        print("   - metadata.parquet")
        print("   - labels.csv")
        print("   - manifest.jsonl")
        if download_images:
            print(f"   - images/ ({stats['images_downloaded']} archivos)")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
