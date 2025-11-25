# Facebook Routes - Estructura Modular

Endpoints organizados por funcionalidad para mayor mantenibilidad.

## Estructura

```
routes/
├── __init__.py          # Integra todos los sub-routers
├── scraper.py           # Endpoints de scraping
├── runs.py              # Consulta de estado y resultados
├── gcs.py               # Operaciones con Google Cloud Storage
├── management.py        # Gestión de runs locales
└── analysis.py          # Análisis completo con IA (DESTACADO)
```

## Endpoints Principales

### 1. Scraping

- `POST /scrape` - Iniciar scraper asíncrono
- `POST /scrape_and_save` - Scrape + descarga de medios

### 2. Consulta de Runs

- `GET /runs/{run_id}` - Estado del run
- `GET /runs/{run_id}/results` - Resultados del scraping
- `GET /health` - Health check

### 3. Google Cloud Storage

- `POST /runs/{run_id}/upload_to_gcs` - Subir prepared/ a GCS
- `GET /gcs/list` - Listar archivos en GCS
- `GET /debug/get_test_file` - Debug de archivos en bucket

### 4. Gestión de Runs

- `GET /runs/list` - Listar todos los runs locales
- `DELETE /runs/{run_id}` - Eliminar un run
- `POST /runs/cleanup` - Limpieza automática de runs antiguos

### 5. Análisis con IA (DESTACADO)

- `POST /analyze-campaign-with-ai` - Análisis end-to-end desde URL
- `POST /analyze-campaign-from-bucket` - Análisis rápido desde GCS

## Endpoints Destacados: Análisis con IA

El endpoint más poderoso del sistema. **Uso simple**:

```bash
POST /api/v1/apify/facebook/analyze-campaign-with-ai
{
  "url": "https://facebook.com/ads/library/?id=123"
}
```

**Hace todo automáticamente:**

1. Scrape anuncios
2. Identifica los mejores
3. Descarga archivos
4. Sube a GCS
5. Analiza con Gemini AI
6. Genera reporte JSON + LaTeX
7. Guarda resultados

**Ver documentación completa**: `docs/ANALYSIS_ENDPOINT.md`

## Configuración

### Variables de Entorno Requeridas

```bash
# Scraping
APIFY_TOKEN=tu_token
APIFY_FACEBOOK_ACTOR=actor_id

# Storage
GOOGLE_APPLICATION_CREDENTIALS=ruta/credentials.json
GOOGLE_BUCKET_NAME=tu_bucket

# Análisis con IA
GOOGLE_GEMINI_API=tu_api_key
PROMPT=prompt_personalizado  # Opcional
```

## Flujo Típico

### Opción 1: Análisis Completo (Recomendado)

```
Usuario → analyze-campaign-with-ai → Reporte completo
```

**1 llamada**, todo automático, 2-5 minutos.

### Opción 2: Control Granular

```
Usuario → scrape → runs/{id} → upload_to_gcs → (análisis manual)
```

Mayor control, más llamadas, útil para pipelines personalizados.

## Arquitectura

### Dependencias Compartidas

- `utils/config.py` - Configuración centralizada (GCS service, paths)
- `models/schemas.py` - Modelos Pydantic compartidos
- `facebook_actor.py` - Cliente de Apify

### Principios de Diseño

- **Separación de responsabilidades**: cada módulo tiene una función clara
- **Reutilización**: código compartido en utils/ y models/
- **Mantenibilidad**: archivos pequeños (~100-500 líneas)
- **Testabilidad**: funciones puras fáciles de testear

## Testing

Cada módulo puede testearse independientemente:

```python
# Ejemplo: test_analysis.py
from routes.analysis import scrape_and_prepare_run

async def test_scrape_and_prepare():
    result = await scrape_and_prepare_run(
        url="https://...",
        count=10,
        top=3
    )
    assert result['run_id']
    assert len(result['manifest']['ads']) == 3
```

## Métricas

- **Total líneas**: ~1,500 (vs 2,626 original)
- **Reducción**: 43% menos código
- **Módulos**: 5 archivos organizados
- **Endpoints**: 15+ endpoints bien estructurados

## Migración desde facebook_routes.py

El archivo original `facebook_routes.py` (2,626 líneas) fue dividido en:

- 40% → scraper.py + runs.py
- 25% → gcs.py
- 15% → management.py
- 20% → analysis.py (nuevo endpoint con IA)

**Beneficios**:

- Más fácil de navegar
- Menor riesgo de merge conflicts
- Onboarding más rápido para nuevos devs
- Tests más específicos y rápidos
