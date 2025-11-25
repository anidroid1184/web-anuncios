"""
Script para probar los endpoints de Gemini via HTTP
"""
import httpx
import json

BASE_URL = "http://localhost:8001/api/v1"

print("="*80)
print("PRUEBA DE ENDPOINTS DE GEMINI")
print("="*80)

# 1. Probar status
print("\n1️⃣ GET /gemini/status")
print("-" * 40)
try:
    response = httpx.get(f"{BASE_URL}/gemini/status", timeout=10.0)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"❌ Error: {e}")

# 2. Probar test de conexión
print("\n2️⃣ GET /gemini/test")
print("-" * 40)
try:
    response = httpx.get(f"{BASE_URL}/gemini/test", timeout=10.0)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Status: {data.get('status')}")
    print(f"Connected: {data.get('connected')}")
    print(f"Model: {data.get('model')}")
    print(f"Response: {data.get('response', 'N/A')[:100]}")
except Exception as e:
    print(f"❌ Error: {e}")

# 3. Listar modelos
print("\n3️⃣ GET /gemini/models")
print("-" * 40)
try:
    response = httpx.get(f"{BASE_URL}/gemini/models", timeout=10.0)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total Models: {data.get('count')}")
    print(f"First 5 models:")
    for model in data.get('models', [])[:5]:
        print(f"  - {model}")
except Exception as e:
    print(f"❌ Error: {e}")

# 4. Análisis de campaña desde URL (ejemplo)
print("\n4️⃣ POST /gemini/analyze-campaign-from-url")
print("-" * 40)
print("⚠️  Este endpoint requiere una URL válida del manifest")
print("Ejemplo de uso:")
print("""
curl -X POST "http://localhost:8001/api/v1/gemini/analyze-campaign-from-url" \\
  -H "Content-Type: application/json" \\
  -d '{
    "manifest_url": "https://storage.googleapis.com/proveedor-1/facebook/yHAmj34fDeR94qUrh/prepared/manifest.json"
  }'
""")

print("\n" + "="*80)
print("✅ Pruebas básicas completadas")
print("="*80)
print("\nPara probar el análisis de campaña, necesitas:")
print("1. Un manifest JSON con URLs públicas de anuncios")
print("2. Ejecutar el POST /gemini/analyze-campaign-from-url con la URL del manifest")
print("\nEl análisis tomará 30-60 segundos y generará un reporte en reports_json/")
