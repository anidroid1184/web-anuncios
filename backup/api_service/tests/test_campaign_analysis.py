"""
Script de prueba para el análisis de campañas con Gemini
"""
from app.services.gemini_service import GeminiService
import os
import json
from pathlib import Path
from app.config.env_loader import load_env

# Cargar variables de entorno
load_env()

# Importar el servicio

print("="*80)
print("PRUEBA DE ANÁLISIS DE CAMPAÑA DE ANUNCIOS CON GEMINI")
print("="*80)

# Inicializar servicio
print("\n🔄 Inicializando GeminiService...")
gemini = GeminiService()
print(f"✅ Servicio inicializado (Modelo: {gemini.default_model})")

# Buscar el manifest de ejemplo
run_id = "yHAmj34fDeR94qUrh"
manifest_path = Path(
    f"storage/facebook/{run_id}/prepared/{run_id}_top10_prepared.json")

if not manifest_path.exists():
    print(f"\n❌ No se encontró el manifest en: {manifest_path}")
    print("Por favor, asegúrate de tener un manifest con datos de anuncios.")
    exit(1)

print(f"\n📂 Leyendo manifest: {manifest_path}")
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest_data = json.load(f)

print(f"   Run ID: {manifest_data.get('run_id')}")
print(f"   Total anuncios: {len(manifest_data.get('ads', []))}")

# Verificar si hay URLs en los anuncios
sample_ad = manifest_data.get('ads', [{}])[0]
if 'files' in sample_ad and len(sample_ad['files']) > 0:
    print(f"   ✅ Anuncios con archivos multimedia: Sí")
    print(f"   Ejemplo: {sample_ad['files'][0].get('url', 'N/A')[:80]}...")
else:
    print(f"   ⚠️  Advertencia: Los anuncios no tienen archivos multimedia")
    print(f"   El análisis se basará en la estructura disponible")

# Realizar análisis
print("\n🔄 Iniciando análisis de campaña con Gemini...")
print("   (Esto puede tomar 30-60 segundos...)")

result = gemini.analyze_ad_campaign_from_manifest(
    manifest_data=manifest_data,
    run_id=run_id
)

if result['status'] == 'success':
    print("\n✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
    print("="*80)
    print(f"📊 Run ID: {result['run_id']}")
    print(f"📄 Reporte guardado en: {result['report_path']}")
    print(f"📝 Nombre del archivo: {result['report_filename']}")

    print("\n📈 RESUMEN DEL ANÁLISIS:")
    summary = result.get('analysis_summary', {})
    print(f"   Total anuncios analizados: {summary.get('total_ads')}")
    print(f"   Fecha de análisis: {summary.get('generated_at')}")

    best = summary.get('best_performer', {})
    if best:
        print(f"\n🏆 MEJOR ANUNCIO:")
        print(f"   Ad ID: {best.get('ad_id')}")
        print(f"   Posición: #{best.get('position')}")
        print(f"   Score General: {best.get('overall_score')}/10")

    # Mostrar algunas recomendaciones clave
    full_analysis = result.get('full_analysis', {})
    recs = full_analysis.get('recommendations', {})

    if recs:
        print(f"\n💡 RECOMENDACIONES CLAVE:")
        for rec in recs.get('for_future_campaigns', [])[:3]:
            print(f"   • {rec}")

    print("\n" + "="*80)
    print("Para ver el análisis completo, abre el archivo JSON generado.")
    print("="*80)

else:
    print("\n❌ ERROR EN EL ANÁLISIS:")
    print(f"   Tipo: {result.get('error_type')}")
    print(f"   Mensaje: {result.get('error')}")
