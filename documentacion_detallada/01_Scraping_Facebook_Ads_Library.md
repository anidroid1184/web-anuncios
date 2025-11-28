# 01. Scraping de Facebook Ads Library

## 📋 Descripción General

El sistema implementa scraping automatizado de anuncios de Facebook Ads Library utilizando la plataforma Apify. Esta funcionalidad permite extraer información completa de anuncios publicitarios activos de forma masiva y estructurada.

## 🎯 Propósito

- Extraer anuncios públicos de Facebook Ads Library
- Obtener metadatos completos de cada anuncio
- Descargar URLs de imágenes y videos asociados
- Organizar datos en formato estructurado (CSV, JSONL)
- Facilitar análisis posterior mediante IA

## 🔧 Implementación Técnica

### Arquitectura

```
Usuario → FastAPI Endpoint → Apify Client → Facebook Ads Library
                ↓
         Almacenamiento Local
                ↓
         Dataset Estructurado
```

### Tecnologías Utilizadas

- **Apify Platform**: Servicio profesional de web scraping
- **Apify Client (Python)**: Cliente oficial para interactuar con Apify
- **Facebook Ads Library**: Fuente pública de datos de anuncios
- **FastAPI**: Framework para crear endpoints REST
- **Pandas**: Manipulación y estructuración de datos

### Módulos y Archivos

- `api_service/app/api/routes/apify/facebook/modules/scraper.py`: Lógica de scraping
- `api_service/app/processors/facebook/extract_dataset.py`: Descarga de datasets
- `api_service/app/services/apify_service.py`: Servicio de integración con Apify

## 📡 Endpoints Disponibles

### POST `/api/v1/apify/facebook/scrape`

Inicia un proceso de scraping asíncrono.

#### Parámetros de Entrada

```json
{
  "query": "nike shoes",
  "maxItems": 100,
  "country": "US",
  "category": "all",
  "mediaType": "all",
  "minDate": "2025-10-01",
  "maxDate": "2025-10-31",
  "proxyConfiguration": {
    "useApifyProxy": true,
    "apifyProxyGroups": ["RESIDENTIAL"]
  }
}
```

#### Parámetros Detallados

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `query` | string | ✅ Sí | - | Término de búsqueda (palabra clave, marca, etc.) |
| `maxItems` | integer | No | 10 | Cantidad máxima de anuncios a extraer |
| `country` | string | No | "ALL" | Código ISO de país (US, MX, ES, etc.) |
| `category` | string | No | "all" | Categoría de anuncios (políticos, vivienda, etc.) |
| `mediaType` | string | No | "all" | Tipo de media (image, video, meme, etc.) |
| `minDate` | string | No | null | Fecha mínima (YYYY-MM-DD) |
| `maxDate` | string | No | null | Fecha máxima (YYYY-MM-DD) |
| `proxyConfiguration` | object | No | Ver abajo | Configuración de proxy |

#### Categorías Disponibles

- `"all"`: Todas las categorías (default)
- `"political_and_issue_ads"`: Anuncios políticos y de asuntos
- `"housing_ads"`: Anuncios de vivienda
- `"employment_ads"`: Anuncios de empleo
- `"credit_ads"`: Productos financieros y crédito

#### Tipos de Media

- `"all"`: Todos los tipos (default)
- `"image"`: Solo imágenes
- `"video"`: Solo videos
- `"meme"`: Solo memes
- `"image_and_meme"`: Imágenes y memes
- `"none"`: Sin archivos multimedia

#### Respuesta

```json
{
  "status": "started",
  "run_id": "xyz789abc123",
  "message": "Scraper de Facebook iniciado. Use GET /runs/xyz789abc123 para consultar estado"
}
```

### GET `/api/v1/apify/facebook/runs/{run_id}`

Consulta el estado de un proceso de scraping.

#### Estados Posibles

- `READY`: Listo para ejecutarse
- `RUNNING`: En progreso
- `SUCCEEDED`: Completado exitosamente
- `FAILED`: Falló
- `ABORTED`: Cancelado

#### Respuesta

```json
{
  "run_id": "xyz789abc123",
  "status": "SUCCEEDED",
  "started_at": "2025-11-24T10:30:00.000Z",
  "finished_at": "2025-11-24T10:35:23.000Z",
  "default_dataset_id": "dataset123abc",
  "stats": {
    "durationMillis": 323000,
    "runTimeSecs": 323.45,
    "computeUnits": 0.045
  }
}
```

### GET `/api/v1/apify/facebook/runs/{run_id}/results`

Obtiene los resultados del scraping completado.

#### Query Parameters

- `limit` (opcional): Cantidad máxima de items (1-1000, default: 100)
- `offset` (opcional): Offset para paginación (default: 0)

#### Respuesta

```json
{
  "status": "success",
  "run_id": "xyz789abc123",
  "count": 100,
  "data": [
    {
      "id": "ad_unique_id_1",
      "adArchiveID": "123456789",
      "pageID": "987654321",
      "pageName": "Nike Official",
      "adCreativeBody": "Discover our new collection...",
      "adCreativeLinkTitle": "New Collection 2025",
      "adSnapshotURL": "https://www.facebook.com/ads/library/?id=123456789",
      "startDate": "2025-10-06",
      "endDate": "2025-10-22",
      "currency": "USD",
      "adSpend": {
        "lower": 100,
        "upper": 500
      },
      "adImpressions": {
        "lower": 10000,
        "upper": 50000
      },
      "mediaType": "image",
      "imageURL": "https://scontent.xx.fbcdn.net/..."
    }
  ]
}
```

## 📊 Estructura de Datos Extraídos

### Campos Principales de un Anuncio

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | string | ID único del anuncio |
| `adArchiveID` | string | ID del archivo de anuncios de Facebook |
| `pageID` | string | ID de la página que publica el anuncio |
| `pageName` | string | Nombre de la página/publicador |
| `adCreativeBody` | string | Texto principal del anuncio |
| `adCreativeLinkCaption` | string | Texto del enlace/CTA |
| `adCreativeLinkDescription` | string | Descripción del enlace |
| `adCreativeLinkTitle` | string | Título del enlace |
| `adSnapshotURL` | string | URL del anuncio en Facebook Ads Library |
| `startDate` | string | Fecha de inicio (YYYY-MM-DD) |
| `endDate` | string | Fecha de fin (YYYY-MM-DD) |
| `currency` | string | Moneda del gasto (USD, EUR, etc.) |
| `adSpend` | object | Rango de gasto estimado {lower, upper} |
| `adImpressions` | object | Rango de impresiones {lower, upper} |
| `mediaType` | string | Tipo de media (image, video) |
| `videoURL` | string | URL del video (si aplica) |
| `imageURL` | string | URL de la imagen (si aplica) |

## 💾 Almacenamiento Local

### Estructura de Directorios

```
api_service/app/processors/datasets/saved_datasets/facebook/
└── {run_id}/
    ├── {run_id}.csv          # Datos en formato CSV
    ├── {run_id}.jsonl        # Datos en formato JSONL
    └── metadata.json         # Información del scraping
```

### Formato CSV

El CSV contiene todas las columnas de los campos principales, facilitando análisis con herramientas como Excel, Pandas, etc.

### Formato JSONL

Cada línea es un objeto JSON válido, ideal para procesamiento streaming y análisis programático.

## 🔄 Flujo de Trabajo Completo

### Paso 1: Iniciar Scraping

```python
import requests

response = requests.post(
    "http://localhost:8001/api/v1/apify/facebook/scrape",
    json={
        "query": "coca cola",
        "maxItems": 100,
        "country": "US"
    }
)

run_id = response.json()["run_id"]
print(f"Scraping iniciado: {run_id}")
```

### Paso 2: Monitorear Estado

```python
import time

while True:
    status_response = requests.get(
        f"http://localhost:8001/api/v1/apify/facebook/runs/{run_id}"
    )
    status = status_response.json()["status"]
    
    if status == "SUCCEEDED":
        print("Scraping completado!")
        break
    elif status == "FAILED":
        print("Scraping falló!")
        break
    
    print(f"Estado: {status}, esperando...")
    time.sleep(10)  # Esperar 10 segundos antes de consultar de nuevo
```

### Paso 3: Obtener Resultados

```python
results_response = requests.get(
    f"http://localhost:8001/api/v1/apify/facebook/runs/{run_id}/results",
    params={"limit": 100}
)

results = results_response.json()
print(f"Total anuncios: {results['count']}")
```

## ⚙️ Configuración

### Variables de Entorno Requeridas

```env
# Token de autenticación de Apify
APIFY_TOKEN=apify_api_xxx...

# Nombre del actor (opcional, tiene default)
APIFY_FACEBOOK_NAME=scrapestorm/facebook-ads-library-scraper---fast-cheap
```

### Configuración de Proxy

El sistema utiliza proxies residenciales por defecto para evitar bloqueos:

```json
{
  "useApifyProxy": true,
  "apifyProxyGroups": ["RESIDENTIAL"]
}
```

**¿Por qué proxies residenciales?**

- Evitan detección como bot
- Mayor tasa de éxito en extracciones
- Mayor estabilidad en conexiones
- Cumplen con términos de servicio de Facebook

## 🎯 Casos de Uso

### Caso 1: Análisis de Competencia

```bash
# Extraer anuncios de competidores
curl -X POST "http://localhost:8001/api/v1/apify/facebook/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "competidor principal",
    "maxItems": 200,
    "country": "MX",
    "minDate": "2025-10-01"
  }'
```

### Caso 2: Análisis de Categoría Específica

```bash
# Anuncios políticos
curl -X POST "http://localhost:8001/api/v1/apify/facebook/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "elecciones",
    "category": "political_and_issue_ads",
    "maxItems": 500
  }'
```

### Caso 3: Solo Videos

```bash
# Extraer solo anuncios con video
curl -X POST "http://localhost:8001/api/v1/apify/facebook/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "producto",
    "mediaType": "video",
    "maxItems": 50
  }'
```

## ⚠️ Limitaciones y Consideraciones

### Limitaciones de Facebook Ads Library

1. **Solo anuncios públicos**: No incluye anuncios privados o de audiencias específicas
2. **Rango de fechas**: Facebook limita búsquedas a aproximadamente 90 días máximo
3. **Gastos e impresiones**: Son rangos estimados, no valores exactos
4. **Disponibilidad**: Depende de la configuración de privacidad del anunciante

### Limitaciones de Apify

1. **Costo**: Cada scraping consume créditos de Apify (~$0.01-0.05 por scraping)
2. **Tiempo**: Los scrapings pueden tomar 3-10 minutos dependiendo del volumen
3. **Rate limiting**: Apify limita la cantidad de scrapings concurrentes

### Mejores Prácticas

1. **Comenzar con valores pequeños**: Prueba con `maxItems=10-50` primero
2. **Polling inteligente**: Espera 10-15 segundos entre consultas de estado
3. **Guardar Run IDs**: Guarda los Run IDs para referencia futura
4. **Manejo de errores**: Implementa reintentos con backoff exponencial
5. **Validación de datos**: Verifica que los datos descargados sean válidos

## 🔍 Troubleshooting

### Problema: Scraping no inicia

**Causas posibles**:
- Token de Apify inválido o expirado
- Parámetros inválidos en el request
- Límite de créditos de Apify alcanzado

**Solución**:
```bash
# Verificar token
curl "http://localhost:8001/api/v1/apify/facebook/health"
```

### Problema: Scraping falla (status=FAILED)

**Causas posibles**:
- Query muy amplia o inválida
- Problemas de conexión con Facebook
- Límites de rate de Apify

**Solución**:
- Simplifica la query
- Espera unos minutos antes de reintentar
- Reduce `maxItems`

### Problema: No se obtienen resultados

**Causas posibles**:
- No hay anuncios que coincidan con los criterios
- Filtros muy restrictivos

**Solución**:
- Amplía los criterios de búsqueda
- Elimina o relaja los filtros
- Verifica que las fechas sean correctas

## 📈 Métricas y Performance

### Tiempos Típicos

| Cantidad de Anuncios | Tiempo Aproximado |
|---------------------|-------------------|
| 10-50 | 2-4 minutos |
| 50-100 | 4-7 minutos |
| 100-200 | 7-12 minutos |
| 200-500 | 12-20 minutos |

### Factores que Afectan el Tiempo

1. **Cantidad de items**: Más items = más tiempo
2. **Complejidad de la query**: Queries complejas pueden tomar más tiempo
3. **Disponibilidad de Facebook**: Tiempos de respuesta de Facebook varían
4. **Proxy availability**: Disponibilidad de proxies residenciales

## 🔐 Seguridad y Privacidad

### Datos Extraídos

- Solo datos públicos disponibles en Facebook Ads Library
- No se accede a información privada de usuarios
- Cumple con términos de servicio de Facebook
- No requiere autenticación de Facebook

### Manejo de Datos

- Los datos se almacenan localmente
- No se comparten con terceros
- Se puede eliminar en cualquier momento
- Cumple con políticas de privacidad

---

**Última actualización**: Noviembre 2025

