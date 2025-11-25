"""
Script rápido para verificar que los endpoints de Facebook están registrados
"""
from fastapi.routing import APIRoute
from main import app
import sys
from pathlib import Path

# Añadir api_service al path
api_service_dir = Path(__file__).parent
sys.path.insert(0, str(api_service_dir))

# Importar la app

# Listar rutas
print("=" * 80)
print("RUTAS REGISTRADAS EN FASTAPI")
print("=" * 80)

facebook_routes = []
other_routes = []


for route in app.routes:
    if isinstance(route, APIRoute):
        route_info = {
            'path': route.path,
            'methods': list(route.methods) if route.methods else [],
            'name': getattr(route, 'name', 'N/A'),
            'tags': list(route.tags) if route.tags else []
        }

        path_lower = route.path.lower()
        has_facebook_tag = 'Facebook' in route_info['tags']

        if 'facebook' in path_lower or has_facebook_tag:
            facebook_routes.append(route_info)
        else:
            other_routes.append(route_info)

print(f"\n✅ ENDPOINTS DE FACEBOOK ({len(facebook_routes)}):")
print("-" * 80)
for r in facebook_routes:
    methods = ", ".join(r['methods'])
    tags = ", ".join(r['tags']) if r['tags'] else "sin tag"
    print(f"{methods:10} {r['path']:60} [{tags}]")

print(f"\n📋 OTROS ENDPOINTS ({len(other_routes)}):")
print("-" * 80)
for r in other_routes[:10]:  # Solo mostrar primeros 10
    methods = ", ".join(r['methods'])
    tags = ", ".join(r['tags']) if r['tags'] else "sin tag"
    print(f"{methods:10} {r['path']:60} [{tags}]")

if len(other_routes) > 10:
    print(f"... y {len(other_routes) - 10} más")

print("\n" + "=" * 80)
print(f"TOTAL RUTAS: {len(facebook_routes) + len(other_routes)}")
print(f"FACEBOOK: {len(facebook_routes)}")
print(f"OTROS: {len(other_routes)}")
print("=" * 80)

# Verificar Swagger
print("\n🌐 DOCUMENTACIÓN:")
print(f"   Swagger UI: http://localhost:8001/docs")
print(f"   ReDoc:      http://localhost:8001/redoc")
print(f"   OpenAPI:    http://localhost:8001/openapi.json")
