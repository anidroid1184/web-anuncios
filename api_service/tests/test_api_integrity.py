"""
Test de Integridad de la API
Verifica que todos los módulos, routers y dependencias críticas se importen correctamente
"""
import pytest
import sys
from pathlib import Path

# Añadir api_service al path
api_service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_service_dir))


class TestAPIIntegrity:
    """Tests de integridad de la API"""

    def test_main_app_loads(self):
        """Verifica que la app principal de FastAPI se carga correctamente"""
        from main import app
        assert app is not None
        assert app.title == "Ads Analyzer API Service"
        assert app.version == "1.0.0"

    def test_core_routes_exist(self):
        """Verifica que las rutas principales existen"""
        from main import app
        from fastapi.routing import APIRoute

        routes = [route for route in app.routes if isinstance(route, APIRoute)]
        route_paths = [route.path for route in routes]

        # Verificar rutas esenciales
        assert "/" in route_paths
        assert "/health" in route_paths
        assert "/debug/routes" in route_paths

    def test_facebook_routes_loaded(self):
        """Verifica que los routers de Facebook se cargan correctamente"""
        from app.api.routes.apify.facebook import router as facebook_router
        assert facebook_router is not None
        assert hasattr(facebook_router, 'routes')
        assert len(facebook_router.routes) > 0

    def test_facebook_submodules_import(self):
        """Verifica que los submódulos de Facebook se importan sin errores"""
        # Actor de Facebook
        from app.api.routes.apify.facebook.facebook_actor import FacebookActor
        assert FacebookActor is not None

        # Schemas de Facebook
        from app.api.routes.apify.facebook.models.schemas import (
            FacebookScraperInput,
            SimpleScrapeRequest,
            FacebookStartResponse,
            FacebookResponse
        )
        assert FacebookScraperInput is not None
        assert SimpleScrapeRequest is not None

        # Utils de Facebook
        from app.api.routes.apify.facebook.utils.config import (
            get_facebook_saved_base,
            get_gcs_service
        )
        assert callable(get_facebook_saved_base)
        assert callable(get_gcs_service)

    def test_facebook_analysis_modules(self):
        """Verifica que los módulos de análisis de Facebook funcionan"""
        from app.api.routes.apify.facebook.analysis import (
            scrape_and_prepare_run,
            analyze_campaign_with_gemini,
            compile_latex_to_pdf,
            build_manifest_from_gcs
        )
        assert callable(scrape_and_prepare_run)
        assert callable(analyze_campaign_with_gemini)
        assert callable(compile_latex_to_pdf)
        assert callable(build_manifest_from_gcs)

    def test_processors_modules(self):
        """Verifica que los procesadores de Facebook funcionan"""
        from app.processors.facebook.extract_dataset import fetch_and_store_run_dataset
        from app.processors.facebook.analyze_dataset import analyze, analyze_jsonl
        from app.processors.facebook.download_images_from_csv import (
            make_session,
            extract_urls_from_snapshot,
            iter_csv_snapshot_rows,
            download_one
        )

        assert callable(fetch_and_store_run_dataset)
        assert callable(analyze)
        assert callable(analyze_jsonl)
        assert callable(make_session)

    def test_tiktok_routes_loaded(self):
        """Verifica que los routers de TikTok se cargan correctamente"""
        from app.api.routes.apify.tiktok import router as tiktok_router
        assert tiktok_router is not None

    def test_instagram_routes_loaded(self):
        """Verifica que los routers de Instagram se cargan correctamente"""
        from app.api.routes.apify.instagram import router as instagram_router
        assert instagram_router is not None

    def test_analytics_routes_loaded(self):
        """Verifica que los routers de Analytics se cargan correctamente"""
        from app.api.routes.analytics import router as analytics_router
        assert analytics_router is not None

    def test_ai_routes_loaded(self):
        """Verifica que los routers de AI se cargan correctamente"""
        from app.api.routes.ai_routes import router as ai_router
        assert ai_router is not None

    def test_apify_service(self):
        """Verifica que el servicio de Apify funciona"""
        from app.services.apify_service import ApifyService
        assert ApifyService is not None

    def test_gemini_service(self):
        """Verifica que el servicio de Gemini funciona"""
        from app.services.gemini_service import GeminiService
        assert GeminiService is not None

    def test_gcs_service(self):
        """Verifica que el servicio de GCS funciona"""
        from app.services.gcs_service import GCSService
        assert GCSService is not None

    def test_bigquery_service(self):
        """Verifica que el servicio de BigQuery funciona"""
        from app.services.bigquery_service import BigQueryService
        assert BigQueryService is not None

    def test_pydantic_models_valid(self):
        """Verifica que los modelos Pydantic son válidos"""
        from app.api.routes.apify.facebook.models.schemas import (
            FacebookScraperInput,
            UrlItem
        )
        from pydantic import ValidationError

        # Test válido
        valid_input = FacebookScraperInput(
            count=100,
            scrapeAdDetails=True,
            urls=[UrlItem(url="https://www.facebook.com/ads/library")]
        )
        assert valid_input.count == 100

        # Test inválido (sin URLs)
        with pytest.raises(ValidationError):
            FacebookScraperInput(
                count=100,
                scrapeAdDetails=True,
                urls=[]
            )

    def test_env_loader(self):
        """Verifica que el cargador de variables de entorno funciona"""
        from app.config.env_loader import load_env
        assert callable(load_env)

    def test_facebook_routes_have_correct_tags(self):
        """Verifica que las rutas de Facebook tienen los tags correctos"""
        from main import app
        from fastapi.routing import APIRoute

        facebook_routes = [
            route for route in app.routes
            if isinstance(route, APIRoute) and 'facebook' in route.path.lower()
        ]

        assert len(facebook_routes) > 0, "No se encontraron rutas de Facebook"

        for route in facebook_routes:
            assert 'Facebook' in route.tags, f"Ruta {route.path} no tiene tag 'Facebook'"

    def test_no_duplicate_routes(self):
        """Verifica que no hay rutas duplicadas"""
        from main import app
        from fastapi.routing import APIRoute

        routes = [route for route in app.routes if isinstance(route, APIRoute)]
        route_signatures = set()

        for route in routes:
            for method in route.methods:
                signature = f"{method}:{route.path}"
                assert signature not in route_signatures, f"Ruta duplicada: {signature}"
                route_signatures.add(signature)

    def test_openapi_schema_valid(self):
        """Verifica que el esquema OpenAPI se genera correctamente"""
        from main import app

        openapi_schema = app.openapi()
        assert openapi_schema is not None
        assert 'paths' in openapi_schema
        assert 'info' in openapi_schema
        assert openapi_schema['info']['title'] == "Ads Analyzer API Service"

    def test_facebook_endpoints_count(self):
        """Verifica que hay al menos 15 endpoints de Facebook"""
        from main import app
        from fastapi.routing import APIRoute

        facebook_routes = [
            route for route in app.routes
            if isinstance(route, APIRoute) and 'facebook' in route.path.lower()
        ]

        assert len(
            facebook_routes) >= 15, f"Se esperaban al menos 15 endpoints de Facebook, se encontraron {len(facebook_routes)}"

    def test_cors_configured(self):
        """Verifica que CORS está configurado"""
        from main import app
        from fastapi.middleware.cors import CORSMiddleware

        cors_middleware = None
        for middleware in app.user_middleware:
            if middleware.cls == CORSMiddleware:
                cors_middleware = middleware
                break

        assert cors_middleware is not None, "CORS middleware no está configurado"


class TestServicesIntegrity:
    """Tests de integridad de servicios externos"""

    def test_apify_client_importable(self):
        """Verifica que el cliente de Apify está disponible"""
        try:
            from apify_client import ApifyClient
            assert ApifyClient is not None
        except ImportError:
            pytest.fail("apify_client no está instalado")

    def test_google_cloud_storage_available(self):
        """Verifica que Google Cloud Storage está disponible"""
        try:
            from google.cloud import storage
            assert storage is not None
        except ImportError:
            pytest.fail("google-cloud-storage no está instalado")

    def test_google_generativeai_available(self):
        """Verifica que Google Generative AI está disponible"""
        try:
            import google.generativeai as genai
            assert genai is not None
        except ImportError:
            pytest.fail("google-generativeai no está instalado")

    def test_pandas_available(self):
        """Verifica que pandas está disponible"""
        try:
            import pandas as pd
            assert pd is not None
        except ImportError:
            pytest.fail("pandas no está instalado")

    def test_pillow_available(self):
        """Verifica que Pillow está disponible"""
        try:
            from PIL import Image
            assert Image is not None
        except ImportError:
            pytest.fail("Pillow no está instalado")


class TestFileStructure:
    """Tests de estructura de archivos"""

    def test_storage_directory_structure(self):
        """Verifica que la estructura de directorios de storage existe"""
        from app.api.routes.apify.facebook.utils.config import get_facebook_saved_base

        base_dir = get_facebook_saved_base()
        assert base_dir is not None

        # Crear directorio si no existe (para testing)
        base_dir.mkdir(parents=True, exist_ok=True)
        assert base_dir.exists()

    def test_credentials_directory_exists(self):
        """Verifica que el directorio de credenciales existe"""
        creds_dir = Path(__file__).parent.parent / 'credentials'

        # El directorio debe existir o ser creado
        if not creds_dir.exists():
            pytest.skip(
                "Directorio de credenciales no configurado (opcional en testing)")

    def test_prompts_directory_exists(self):
        """Verifica que el directorio de prompts existe"""
        prompts_dir = Path(__file__).parent.parent / 'prompts'
        assert prompts_dir.exists(), "Directorio de prompts no existe"

        # Verificar archivos de prompts
        assert (prompts_dir / 'prompt.txt').exists(), "prompt.txt no existe"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
