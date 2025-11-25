"""
Script de prueba rápida para el endpoint completo de análisis con IA
"""
import httpx
import json

BASE_URL = "http://localhost:8001/api/v1/apify/facebook"

print("="*80)
print("🤖 PRUEBA: ANÁLISIS COMPLETO DE CAMPAÑA CON GEMINI AI")
print("="*80)

# URL de ejemplo del manifest (debes reemplazarla con una real)
MANIFEST_URL = "https://storage.googleapis.com/proveedor-1/facebook/yHAmj34fDeR94qUrh/prepared/yHAmj34fDeR94qUrh_top10_prepared.json"

print("\n📋 Configuración:")
print(f"   Endpoint: {BASE_URL}/analyze-campaign-with-ai")
print(f"   Manifest URL: {MANIFEST_URL}")

print("\n🔄 Enviando request...")
print("   (Esto tomará 30-90 segundos para el análisis completo)")

try:
    response = httpx.post(
        f"{BASE_URL}/analyze-campaign-with-ai",
        json={
            "manifest_url": MANIFEST_URL
        },
        timeout=120.0  # 2 minutos de timeout
    )

    print(f"\n📊 Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        print("\n✅ ANÁLISIS COMPLETADO CON ÉXITO!")
        print("="*80)

        print(f"\n📈 Resumen:")
        print(f"   Run ID: {data.get('run_id')}")
        print(f"   Anuncios analizados: {data.get('total_ads_analyzed')}")
        print(f"   Reporte guardado: {data.get('report_filename')}")
        print(f"   Path completo: {data.get('report_path')}")

        summary = data.get('analysis_summary', {})
        best = summary.get('best_performer', {})

        if best:
            print(f"\n🏆 MEJOR ANUNCIO:")
            print(f"   Ad ID: {best.get('ad_id')}")
            print(f"   Posición: #{best.get('position')}")
            print(f"   Score General: {best.get('overall_score')}/10")

        print(f"\n🤖 IA Metadata:")
        ai_meta = data.get('ai_metadata', {})
        print(f"   Modelo usado: {ai_meta.get('model_used')}")

        print("\n" + "="*80)
        print("Para ver el análisis completo, consulta el archivo JSON generado:")
        print(f"   {data.get('report_path')}")
        print("="*80)

    else:
        print(f"\n❌ Error {response.status_code}:")
        print(json.dumps(response.json(), indent=2))

except httpx.TimeoutException:
    print("\n⏱️ TIMEOUT: El análisis está tomando más de 2 minutos.")
    print("Esto puede ocurrir con campañas muy grandes.")
    print("El análisis puede seguir ejecutándose en el servidor.")

except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "="*80)
print("NOTA: Reemplaza MANIFEST_URL con la URL real de tu manifest")
print("="*80)
