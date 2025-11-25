"""
Script de prueba para el servicio de Gemini
"""
from app.services.gemini_service import GeminiService
import os
from app.config.env_loader import load_env

# Cargar variables de entorno
load_env()

# Verificar que la API key está cargada
api_key = os.getenv('GOOGLE_GEMINI_API')
print(f"✅ API Key cargada: {'Sí' if api_key else 'No'}")
if api_key:
    print(f"   Longitud: {len(api_key)} caracteres")

# Importar y probar el servicio

print("\n🔄 Inicializando GeminiService...")
gemini = GeminiService()
print(f"✅ Servicio inicializado")
print(f"   Modelo por defecto: {gemini.default_model}")

# Probar conexión
print("\n🔄 Probando conexión con Gemini...")
result = gemini.test_connection()

if result['status'] == 'success':
    print("✅ Conexión exitosa!")
    print(f"   Modelo: {result['model']}")
    print(f"   Prompt de prueba: {result['test_prompt']}")
    print(f"   Respuesta: {result['response']}")
    print(f"   Metadata: {result['metadata']}")
else:
    print("❌ Error en la conexión:")
    print(f"   Tipo: {result.get('error_type')}")
    print(f"   Mensaje: {result.get('error')}")

# Listar modelos disponibles
print("\n🔄 Listando modelos disponibles...")
models = gemini.list_models()
print(f"✅ Modelos encontrados: {len(models)}")
for i, model in enumerate(models[:5], 1):  # Mostrar solo los primeros 5
    print(f"   {i}. {model}")
if len(models) > 5:
    print(f"   ... y {len(models) - 5} más")

print("\n✅ Prueba completada!")
