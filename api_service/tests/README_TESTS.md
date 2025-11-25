# Tests de Integridad de la API

## Descripción

Suite completa de tests que verifica la integridad de toda la API, incluyendo:

- ✅ Carga correcta de la aplicación FastAPI
- ✅ Registro de todos los routers (Facebook, TikTok, Instagram, Analytics, AI)
- ✅ Importación de módulos sin errores
- ✅ Validación de modelos Pydantic
- ✅ Configuración de CORS
- ✅ Generación correcta del esquema OpenAPI
- ✅ Verificación de dependencias externas
- ✅ Estructura de directorios

## Ejecución

### Ejecutar todos los tests

```bash
cd api_service
pytest tests/test_api_integrity.py -v
```

### Ejecutar con más detalle

```bash
pytest tests/test_api_integrity.py -v --tb=short
```

### Ejecutar solo una clase de tests

```bash
# Solo tests de API
pytest tests/test_api_integrity.py::TestAPIIntegrity -v

# Solo tests de servicios
pytest tests/test_api_integrity.py::TestServicesIntegrity -v

# Solo tests de estructura de archivos
pytest tests/test_api_integrity.py::TestFileStructure -v
```

### Ejecutar un test específico

```bash
pytest tests/test_api_integrity.py::TestAPIIntegrity::test_facebook_routes_loaded -v
```

## Resultados Esperados

```
===================== 29 passed, 7 warnings in 3.04s =====================
```

Los tests verifican:

### 1. TestAPIIntegrity (21 tests)

- `test_main_app_loads` - App FastAPI se carga correctamente
- `test_core_routes_exist` - Rutas principales existen (/, /health, /debug/routes)
- `test_facebook_routes_loaded` - Router de Facebook se carga sin errores
- `test_facebook_submodules_import` - Submódulos de Facebook importan correctamente
- `test_facebook_analysis_modules` - Módulos de análisis funcionan
- `test_processors_modules` - Procesadores de datasets funcionan
- `test_tiktok_routes_loaded` - Router de TikTok se carga
- `test_instagram_routes_loaded` - Router de Instagram se carga
- `test_analytics_routes_loaded` - Router de Analytics se carga
- `test_ai_routes_loaded` - Router de AI se carga
- `test_apify_service` - Servicio de Apify importa correctamente
- `test_gemini_service` - Servicio de Gemini importa correctamente
- `test_gcs_service` - Servicio de GCS importa correctamente
- `test_bigquery_service` - Servicio de BigQuery importa correctamente
- `test_pydantic_models_valid` - Modelos Pydantic validan correctamente
- `test_env_loader` - Cargador de variables de entorno funciona
- `test_facebook_routes_have_correct_tags` - Rutas de Facebook tienen tag correcto
- `test_no_duplicate_routes` - No hay rutas duplicadas
- `test_openapi_schema_valid` - Esquema OpenAPI se genera correctamente
- `test_facebook_endpoints_count` - Al menos 15 endpoints de Facebook registrados
- `test_cors_configured` - CORS está configurado

### 2. TestServicesIntegrity (5 tests)

- `test_apify_client_importable` - apify_client instalado
- `test_google_cloud_storage_available` - google-cloud-storage instalado
- `test_google_generativeai_available` - google-generativeai instalado
- `test_pandas_available` - pandas instalado
- `test_pillow_available` - Pillow instalado

### 3. TestFileStructure (3 tests)

- `test_storage_directory_structure` - Directorio storage existe
- `test_credentials_directory_exists` - Directorio credentials existe
- `test_prompts_directory_exists` - Directorio prompts existe

## Warnings Esperados

Los siguientes warnings son esperados y no afectan la funcionalidad:

- **PydanticDeprecatedSince20**: Algunos modelos usan configuración de Pydantic v1 (class-based config). Se debe migrar a ConfigDict en el futuro.
- **Field extra kwargs**: Algunos campos usan `example` en lugar de `json_schema_extra`.

## Troubleshooting

### Error: ModuleNotFoundError

Si algún test falla con `ModuleNotFoundError`, instala las dependencias:

```bash
pip install -r requirements.txt
```

### Error: IndentationError

Si hay errores de indentación, ya fueron corregidos en `apify_service.py`.

### Error: No module named 'deprecated'

Este error es esperado y no afecta los tests. El módulo `deprecated.gcloud_routes` ya no se usa.

## Integración Continua

Estos tests se pueden integrar en un pipeline CI/CD:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest tests/test_api_integrity.py -v
```

## Mantenimiento

Actualizar tests cuando:

- Se agreguen nuevos routers o endpoints
- Se cambien modelos Pydantic
- Se agreguen nuevas dependencias
- Se modifique la estructura de archivos
