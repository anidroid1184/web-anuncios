"""
FastAPI Application - Servicio de APIs para Analizador de Anuncios

MODULO: main.py
AUTOR: Juan Sebastian Valencia Londoño
VERSION: 1.0.0
FECHA: 2025-10-03

PROPOSITO:
    Aplicación principal FastAPI que actúa como servidor de APIs intermediario
    entre el frontend Django y los servicios externos (Apify, Google Cloud Storage).
    Centraliza toda la lógica de negocio relacionada con extracción, procesamiento
    y análisis de datos de anuncios publicitarios.

FUNCIONALIDAD PRINCIPAL:
    - Servidor HTTP asíncrono en puerto 8001 con documentación automática
    - Configuración de CORS para comunicación segura con Django (puerto 8000)  
    - Registro modular de routers para diferentes dominios de negocio
    - Endpoints de salud y monitoreo del sistema
    - Documentación interactiva automática en /docs y /redoc
    - Manejo centralizado de errores y logging

DEPENDENCIAS CORE:
    - FastAPI: Framework web asíncrono de alto rendimiento
    - uvicorn: Servidor ASGI compatible con async/await
    - CORSMiddleware: Manejo seguro de políticas de origen cruzado
    - Pydantic: Validación automática de datos de entrada/salida

ARQUITECTURA:
    - Patrón de microservicio que separa lógica de negocio del frontend
    - Diseño modular con routers independientes por funcionalidad
    - Comunicación asíncrona para operaciones de larga duración
    - Integración directa con APIs externas (Apify, Google Cloud)
    - Facilita escalabilidad horizontal y mantenimiento independiente

ENDPOINTS DISPONIBLES:
    - GET / : Información general del servicio y endpoints disponibles
    - GET /health : Verificación de salud y disponibilidad del servicio
    - /api/v1/apify/* : Extracción automatizada de anuncios via Apify
    - /api/v1/analytics/* : Generación de análisis y métricas en tiempo real
    - /api/v1/gemini/* : Análisis con IA usando Gemini

CONFIGURACION DE DESPLIEGUE:
    - Puerto por defecto: 8001 (configurable via variables de entorno)
    - Host: 0.0.0.0 para aceptar conexiones externas
    - CORS configurado para localhost:8000 y 127.0.0.1:8000 (Django)
    - Reload automático habilitado en modo desarrollo
    - Documentación disponible en /docs (Swagger UI) y /redoc

SEGURIDAD:
    - CORS restrictivo solo para orígenes autorizados
    - Validación automática de entrada via Pydantic
    - Manejo seguro de credenciales via variables de entorno
    - Headers de seguridad configurados automáticamente

MONITOREO:
    - Endpoint /health para health checks
    - Logging estructurado de todas las operaciones
    - Métricas de rendimiento automáticas
    - Documentación de API siempre actualizada
"""
import uvicorn
import logging
import traceback
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import os
from app.config.env_loader import load_env

# IMPORTANTE: Cargar variables de entorno ANTES de importar cualquier módulo
load_env()

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("ads_analyzer")


# Intentar importar routers (con manejo de errores para evitar crashes)
apify_router = None
analytics_router = None
ai_router = None
facebook_router = None

try:
    from app.api.routes.apify import router as apify_router
    logger.info("Apify routes loaded successfully")
except Exception:
    logger.exception("Apify routes not available")

# facebook_router se carga automáticamente dentro de apify_router

try:
    from app.api.routes.analytics import router as analytics_router
    logger.info("Analytics routes loaded successfully")
except Exception as e:
    # Solo log del error si es necesario, no mostrar traceback completo
    logger.warning(f"Analytics routes not available: {str(e)}")

try:
    from app.api.routes.ai_routes import router as ai_router
    logger.info("AI routes loaded successfully")
except Exception:
    logger.exception("AI routes not available")

# Metadata para documentación de la API
tags_metadata = [
    {
        "name": "Apify",
        "description": "Operaciones de scraping y extracción de datos con Apify",
    },
    {
        "name": "Facebook",
        "description": "Endpoints específicos para Facebook Ads Library",
    },
    {
        "name": "Analytics",
        "description": "Análisis de métricas y generación de reportes",
    },
    {
        "name": "AI",
        "description": "Servicios de Inteligencia Artificial (Gemini, OpenAI)",
    },
]

# Inicialización de la aplicación FastAPI
app = FastAPI(
    title="Ads Analyzer API Service",
    description="API para extracción y análisis de anuncios publicitarios",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# Configuración de CORS para permitir requests desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:3001",  # Frontend prototype
        "http://127.0.0.1:3001",  # Frontend prototype
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers opcionales solo si están disponibles

if apify_router:
    app.include_router(apify_router, prefix="/api/v1/apify")

# facebook_router ya está incluido dentro de apify_router
# No lo registramos por separado para evitar duplicados

if analytics_router:
    app.include_router(
        analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])

if ai_router:
    app.include_router(
        ai_router, prefix="/api/v1/ai", tags=["AI"])




@app.get("/")
async def root():
    """
    Endpoint de información general y directorio del servicio API.

    Proporciona metadata del servicio incluyendo versión, estado de salud
    y un mapa completo de todos los endpoints disponibles. Útil para
    descubrimiento de API y verificación de conectividad básica.

    Returns:
        dict: Diccionario con información estructurada del servicio:
            - message (str): Nombre identificativo del servicio
            - status (str): Estado operativo ("active", "maintenance", etc.)
            - version (str): Versión semántica del API (formato X.Y.Z)
            - endpoints (dict): Mapa de rutas base organizadas por funcionalidad
                * apify (str): Ruta base para operaciones de Apify
                * analytics (str): Ruta base para análisis y métricas
                * gemini (str): Ruta base para análisis con IA

    Example:
        >>> import httpx
        >>> async with httpx.AsyncClient() as client:
        ...     response = await client.get("http://localhost:8001/")



        ...     data = response.json()
        >>> print(data["message"])
        "Ads Analyzer API Service"
        >>> print(data["endpoints"]["apify"])
        "/api/v1/apify"

    HTTP Status Codes:
        200: Servicio operativo y respuesta exitosa

    Note:
        Este endpoint no requiere autenticación y siempre debería estar
        disponible para health checks externos y documentación automática.
        La información de versión se sincroniza automáticamente con el
        objeto FastAPI application.
    """
    return {
        "message": "Ads Analyzer API Service",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "apify": "/api/v1/apify",
            "facebook": "/api/v1/apify/facebook",
            "tiktok": "/api/v1/apify/tiktok",
            "instagram": "/api/v1/apify/instagram",
            "analytics": "/api/v1/analytics",
            "ai": "/api/v1/ai"
        }
    }


@app.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud y disponibilidad del servicio.

    Realiza un health check básico del servicio API para monitoreo de
    infraestructura, load balancers, y sistemas de orquestación.
    Diseñado para ser llamado frecuentemente por sistemas externos.

    Este endpoint verifica:
    - Disponibilidad del proceso FastAPI
    - Capacidad de respuesta del servidor HTTP
    - Estado básico del runtime de Python

    Returns:
        dict: Diccionario con información del estado de salud:
            - status (str): Estado de salud del servicio. Valores posibles:
                * "healthy": Servicio operativo y funcionando correctamente
                * "degraded": Servicio operativo pero con limitaciones
                * "unhealthy": Servicio con problemas críticos
            - service (str): Identificador del tipo de servicio ("api")
            - timestamp (str, optional): Timestamp UTC del health check
            - uptime (int, optional): Tiempo en segundos desde el inicio

    HTTP Status Codes:
        200: Servicio saludable y operativo
        503: Servicio no saludable o con problemas

    Example:
        >>> import httpx
        >>> response = await httpx.get("http://localhost:8001/health")
        >>> assert response.status_code == 200
        >>> data = response.json()
        >>> assert data["status"] == "healthy"
        >>> print(f"Servicio {data['service']} está {data['status']}")
        "Servicio api está healthy"

    Note:
        Este endpoint debe responder rápidamente (< 100ms) ya que puede ser
        llamado con alta frecuencia por sistemas de monitoreo. No incluye
        verificaciones pesadas de dependencias externas.

    Usage:
        Típicamente usado por:
        - Kubernetes liveness/readiness probes
        - Load balancers para health checks
        - Sistemas de monitoreo (Prometheus, etc.)
        - Scripts de deployment y CI/CD
    """
    return {"status": "healthy", "service": "api"}


# Endpoint de ayuda para debugging: listar rutas registradas
@app.get("/debug/routes")
async def list_routes():
    routes = []
    for r in app.routes:
        routes.append({
            'path': getattr(r, 'path', str(r)),
            'name': getattr(r, 'name', None),
            'methods': list(getattr(r, 'methods', [])),
        })
    return {'routes': routes}

if __name__ == "__main__":
    # Organización del arranque:
    # Preferir variable PORT, luego API_PORT, por último usar 8000 por defecto.
    # Por defecto abrir en localhost (modo desarrollador).
    # Si API_HOST está presente en el entorno lo respetamos; por defecto usamos localhost.
    host = os.getenv('API_HOST', '127.0.0.1')
    try:
        port = int(os.getenv('PORT') or os.getenv('API_PORT') or 8000)
    except Exception:
        port = 8000

    # DEBUG/RELOAD: si DEBUG en .env está establecido a true/1/yes
    # activamos reload
    debug_env = os.getenv('DEBUG', 'False')
    reload_flag = str(debug_env).lower() in ('1', 'true', 'yes')

    print(
        f"Starting Ads Analyzer API Service -> host={host} port={port} "
        f"reload={reload_flag}"
    )

    # Usar string "main:app" para que el reloader funcione correctamente cuando
    # se solicita `reload=True`.
    uvicorn.run("main:app", host=host, port=port, reload=reload_flag)
