"""
Script de verificación de configuración del .env
Valida que todas las variables críticas estén presentes
"""
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Cargar .env desde la raíz del proyecto
project_root = Path(__file__).parent
env_file = project_root / '.env'

if not env_file.exists():
    print(f"❌ ERROR: Archivo .env no encontrado en {env_file}")
    sys.exit(1)

# Cargar variables de entorno
load_dotenv(env_file)

print("="*80)
print("🔍 VERIFICACIÓN DE CONFIGURACIÓN DEL .ENV")
print("="*80)
print(f"📂 Archivo: {env_file}")
print()

# Variables críticas para verificar
CRITICAL_VARS = {
    "OPENAI_API_KEY": "OpenAI API para análisis con GPT-4 Vision",
    "APIFY_TOKEN": "Token de Apify para scraping",
    "GOOGLE_GEMINI_API": "API de Google Gemini",
    "GOOGLE_APPLICATION_CREDENTIALS": "Credenciales de Google Cloud Storage",
    "GOOGLE_BUCKET_NAME": "Nombre del bucket de GCS",
}

OPTIONAL_VARS = {
    "OPEN_API_KEY": "Alias legacy de OPENAI_API_KEY (compatibilidad)",
    "API_PORT": "Puerto del servidor API",
    "DEBUG": "Modo debug",
    "PROMPT_FILE": "Archivo de prompt personalizado",
}

print("📋 VARIABLES CRÍTICAS:")
print("-" * 80)

critical_missing = []
for var, description in CRITICAL_VARS.items():
    value = os.getenv(var)
    if value:
        # Mostrar solo los primeros 20 caracteres de valores sensibles
        if "KEY" in var or "TOKEN" in var:
            display_value = value[:20] + "..." if len(value) > 20 else value
        else:
            display_value = value
        print(f"✅ {var}: {display_value}")
        print(f"   └─ {description}")
    else:
        print(f"❌ {var}: NO CONFIGURADA")
        print(f"   └─ {description}")
        critical_missing.append(var)

print()
print("📝 VARIABLES OPCIONALES:")
print("-" * 80)

for var, description in OPTIONAL_VARS.items():
    value = os.getenv(var)
    if value:
        if "KEY" in var or "TOKEN" in var:
            display_value = value[:20] + "..." if len(value) > 20 else value
        else:
            display_value = value
        print(f"✅ {var}: {display_value}")
    else:
        print(f"⚠️  {var}: No configurada (opcional)")
    print(f"   └─ {description}")

print()
print("="*80)

# Verificación especial: OPENAI_API_KEY vs OPEN_API_KEY
openai_key = os.getenv("OPENAI_API_KEY")
open_api_key = os.getenv("OPEN_API_KEY")

if openai_key and open_api_key:
    if openai_key == open_api_key:
        print("✅ OPENAI_API_KEY y OPEN_API_KEY tienen el mismo valor (correcto)")
    else:
        print("⚠️  OPENAI_API_KEY y OPEN_API_KEY tienen valores diferentes")
elif openai_key:
    print("✅ OPENAI_API_KEY configurada (nombre estándar)")
    print("⚠️  OPEN_API_KEY no configurada (considera añadirla como alias)")
elif open_api_key:
    print("⚠️  Solo OPEN_API_KEY está configurada (usar OPENAI_API_KEY)")
    print("   Solución: Añadir línea: OPENAI_API_KEY=" +
          open_api_key[:20] + "...")

print("="*80)

# Resultado final
if critical_missing:
    print(f"\n❌ CONFIGURACIÓN INCOMPLETA")
    print(f"   Faltan {len(critical_missing)} variables críticas:")
    for var in critical_missing:
        print(f"   - {var}")
    print(f"\n   Edita el archivo {env_file} y añade las variables faltantes")
    sys.exit(1)
else:
    print("\n✅ CONFIGURACIÓN COMPLETA")
    print("   Todas las variables críticas están configuradas correctamente")
    print("   El servidor API puede iniciarse sin problemas")
    sys.exit(0)
