"""
Script de Verificación - Facebook Routes Package
Verifica que el paquete refactorizado esté correctamente integrado
"""

import sys
from pathlib import Path

# Agregar api_service al path
api_service_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(api_service_root))

print("=" * 60)
print("Facebook Routes - Verificación de Integración")
print("=" * 60)

# Test 1: Verificar estructura de archivos
print("\n[1/6] Verificando estructura de archivos...")
package_root = Path(__file__).resolve().parent
expected_files = [
    "__init__.py",
    "config.py",
    "models.py",
    "services/__init__.py",
    "services/scraping_service.py",
    "services/runs_service.py",
    "services/storage_service.py",
    "services/preparation_service.py",
    "services/upload_service.py",
    "services/analysis_service.py",
    "endpoints/__init__.py",
    "endpoints/scraping.py",
    "endpoints/runs.py",
    "endpoints/storage.py",
    "endpoints/workflows.py",
    "endpoints/analysis.py",
]

missing = []
for file in expected_files:
    if not (package_root / file).exists():
        missing.append(file)

if missing:
    print(f"   ✗ Archivos faltantes: {', '.join(missing)}")
else:
    print(f"   ✓ Todos los archivos presentes ({len(expected_files)} archivos)")

# Test 2: Verificar imports básicos
print("\n[2/6] Verificando imports básicos...")
try:
    from ..config import PathResolver, path_resolver
    print("   ✓ config.PathResolver")
except Exception as e:
    print(f"   ✗ config.PathResolver: {e}")

try:
    from ..models import (
        SimpleScrapeRequest,
        FacebookScraperInput,
        WorkflowRequest
    )
    print("   ✓ models (SimpleScrapeRequest, FacebookScraperInput, etc.)")
except Exception as e:
    print(f"   ✗ models: {e}")

# Test 3: Verificar servicios
print("\n[3/6] Verificando servicios...")
services_ok = 0
services_total = 7

try:
    from ..services import (
        ScrapingService,
        RunsService,
        StorageService,
        PreparationService,
        UploadService,
        AnalysisService,
        HealthService
    )
    services_ok = 7
    print(f"   ✓ Todos los servicios importados ({services_ok}/{services_total})")
except Exception as e:
    print(f"   ✗ Error importando servicios: {e}")

# Test 4: Verificar routers de endpoints
print("\n[4/6] Verificando routers de endpoints...")
routers_ok = 0
routers_total = 5

try:
    from ..endpoints import (
        scraping_router,
        runs_router,
        storage_router,
        workflows_router,
        analysis_router
    )
    routers_ok = 5
    print(f"   ✓ Todos los routers importados ({routers_ok}/{routers_total})")
except Exception as e:
    print(f"   ⚠ Error importando routers (probablemente dependencias): {e}")

# Test 5: Verificar router principal
print("\n[5/6] Verificando router principal...")
try:
    from .. import router
    routes_count = len(router.routes)
    print(f"   ✓ Router principal cargado ({routes_count} rutas registradas)")
    
    if routes_count > 0:
        print("\n   Rutas disponibles:")
        for route in router.routes[:10]:  # Mostrar primeras 10
            print(f"      - {route.methods} {route.path}")
        if routes_count > 10:
            print(f"      ... y {routes_count - 10} más")
    else:
        print("   ⚠ Router vacío (dependencias faltantes)")
        
except Exception as e:
    print(f"   ✗ Error con router principal: {e}")

# Test 6: Verificar integración con sistema
print("\n[6/6] Verificando integración con sistema...")
try:
    from app.api.routes.apify.facebook import router as facebook_router
    print(f"   ✓ Router integrado en facebook/ ({len(facebook_router.routes)} rutas)")
except Exception as e:
    print(f"   ⚠ Error en integración: {e}")

# Resumen
print("\n" + "=" * 60)
print("RESUMEN")
print("=" * 60)

total_tests = 6
passed_tests = 0

if not missing:
    passed_tests += 1
if services_ok == services_total:
    passed_tests += 1

print(f"\nTests completados: {passed_tests}/{total_tests}")

if passed_tests == total_tests:
    print("\n✓ ¡Paquete completamente funcional!")
elif passed_tests >= total_tests - 1:
    print("\n⚠ Paquete funcional con advertencias menores")
    print("  (Probablemente faltan dependencias opcionales como apify_client)")
else:
    print("\n✗ Se encontraron problemas en el paquete")
    print("  Revisa los errores arriba")

print("\n" + "=" * 60)
