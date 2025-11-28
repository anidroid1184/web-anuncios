# 10. Arquitectura del Sistema

## 📋 Descripción General

Este documento describe la arquitectura completa del sistema Analizador de Anuncios de Facebook, incluyendo componentes principales, flujos de datos, tecnologías utilizadas, patrones de diseño y decisiones arquitectónicas clave.

## 🎯 Visión General

El sistema está diseñado como una arquitectura de microservicios moderna que separa las responsabilidades entre scraping, procesamiento, análisis con IA y generación de reportes. Utiliza un patrón API-first con FastAPI y una interfaz web simple para facilitar la interacción.

## 🏗️ Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                     │
│                                                              │
│  ┌──────────────────┐          ┌──────────────────┐        │
│  │  Frontend Web    │          │   API REST       │        │
│  │  (Prototipo)     │ ◄──────► │   FastAPI        │        │
│  │  Puerto 3001     │  HTTP    │   Puerto 8001    │        │
│  └──────────────────┘          └────────┬─────────┘        │
└──────────────────────────────────────────┼──────────────────┘
                                           │
┌──────────────────────────────────────────┼──────────────────┐
│                    CAPA DE SERVICIOS                        │
│                                           │                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──┴──────────┐      │
│  │   Apify      │  │   OpenAI     │  │  ReportLab  │      │
│  │   Service    │  │   Service    │  │  Service    │      │
│  └──────────────┘  └──────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────┘
                                           │
┌──────────────────────────────────────────┼──────────────────┐
│                    CAPA DE DATOS                            │
│                                           │                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Sistema de Archivos Local                    │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │  │
│  │  │  Datasets  │  │   Media    │  │  Reports   │    │  │
│  │  │  (CSV/JSON)│  │ (Imágenes) │  │   (PDFs)   │    │  │
│  │  └────────────┘  └────────────┘  └────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Componentes Principales

### 1. Backend API (FastAPI)

#### Ubicación
```
api_service/
└── app/
    ├── api/
    │   └── routes/
    │       ├── apify/
    │       │   └── facebook/
    │       │       └── modules/
    │       ├── analytics/
    │       └── ai_routes.py
    ├── processors/
    │   ├── datasets/
    │   ├── facebook/
    │   ├── media_preparation/
    │   └── video_processor/
    ├── services/
    │   ├── apify_service.py
    │   └── pdf_generator/
    ├── config/
    │   └── env_loader.py
    └── models/
```

#### Características

- **Framework**: FastAPI (ASGI)
- **Servidor**: Uvicorn
- **Puerto**: 8001
- **Paradigma**: Asíncrono (async/await)
- **Validación**: Pydantic models
- **Documentación**: Swagger/OpenAPI automática

#### Estructura Modular

```
routes/
├── apify/               # Scraping con Apify
│   ├── facebook/       # Endpoints específicos de Facebook
│   ├── tiktok/         # Endpoints de TikTok
│   └── instagram/      # Endpoints de Instagram
├── analytics/          # Análisis y métricas
└── ai_routes.py        # Servicios de IA
```

### 2. Frontend Prototipo

#### Ubicación
```
frontend/prototype/
├── index.html
├── styles.css
└── script.js
```

#### Características

- **Stack**: HTML5 + CSS3 + JavaScript (ES6+)
- **Servidor**: HTTP Server simple (Python)
- **Puerto**: 3001
- **Sin frameworks**: JavaScript vanilla para simplicidad
- **Iconos**: Lucide Icons
- **Fuentes**: Google Fonts (Outfit)

### 3. Procesadores de Datos

#### Estructura

```
processors/
├── datasets/              # Gestión de datasets
│   └── saved_datasets/   # Datasets descargados
├── facebook/             # Procesadores específicos Facebook
│   ├── extract_dataset.py
│   └── download_images_from_csv.py
├── media_preparation/    # Preparación de multimedia
│   ├── image_optimizer.py
│   ├── batch_processor.py
│   └── async_encoder.py
└── video_processor/      # Procesamiento de videos
    └── frame_extractor.py
```

#### Responsabilidades

- **Extracción**: Descarga de datasets desde Apify
- **Procesamiento**: Optimización de imágenes y videos
- **Organización**: Estructuración de archivos
- **Validación**: Verificación de integridad

### 4. Servicios Externos

#### Apify Platform

**Propósito**: Scraping automatizado de Facebook Ads Library

**Integración**:
```python
from apify_client import ApifyClient

client = ApifyClient(token=APIFY_TOKEN)
run = client.actor("scrapestorm/facebook-ads-library-scraper---fast-cheap").call(input)
```

**Responsabilidades**:
- Extracción de anuncios
- Obtención de metadatos
- URLs de multimedia

#### OpenAI GPT-4o

**Propósito**: Análisis inteligente de anuncios

**Integración**:
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
response = await client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    response_format={"type": "json_object"}
)
```

**Responsabilidades**:
- Análisis visual de imágenes
- Análisis de frames de video
- Generación de insights
- Rankings y recomendaciones

## 🔄 Flujos de Datos Principales

### Flujo 1: Análisis Completo desde URL

```
1. Usuario → Frontend
   ↓
2. Frontend → API: POST /analyze-url-with-download
   ↓
3. API → Apify: Iniciar scraping
   ↓
4. Apify → Facebook Ads Library: Extraer anuncios
   ↓
5. Apify → API: Dataset completo
   ↓
6. API → Almacenamiento Local: Guardar CSV + Multimedia
   ↓
7. API → Procesador de Videos: Extraer frames
   ↓
8. API → Procesador de Imágenes: Optimizar imágenes
   ↓
9. API → Codificador Base64: Codificar multimedia
   ↓
10. API → OpenAI: Enviar payload con imágenes
    ↓
11. OpenAI → API: Análisis JSON estructurado
    ↓
12. API → Generador PDF: Crear reporte
    ↓
13. API → Frontend: Retornar paths (PDF, JSON)
    ↓
14. Frontend: Descargar PDF automáticamente
```

### Flujo 2: Análisis desde Run ID Existente

```
1. Usuario → Frontend: Ingresa Run ID
   ↓
2. Frontend → API: POST /analyze-local-and-pdf?run_id=X
   ↓
3. API → Verificar Dataset Local
   ↓
4. Si falta → API → Apify: Descargar dataset
   ↓
5. API → Procesadores: Videos + Imágenes
   ↓
6. API → OpenAI: Análisis
   ↓
7. API → PDF Generator: Reporte
   ↓
8. API → Frontend: Resultados
```

## 🗂️ Estructura de Directorios

### Árbol de Directorios Principal

```
web_analizador_anuncios/
├── api_service/                    # Backend principal
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/            # Endpoints REST
│   │   ├── processors/            # Procesadores de datos
│   │   ├── services/              # Servicios externos
│   │   ├── models/                # Modelos de datos
│   │   └── config/                # Configuración
│   ├── main.py                    # Punto de entrada FastAPI
│   └── prompts/                   # Prompts personalizables
│
├── frontend/                       # Frontend
│   └── prototype/                 # Prototipo web
│
├── docs/                          # Documentación de API
├── Documentacion_extensa/         # Documentación detallada
├── scripts/                       # Scripts de inicio
├── start.py                       # Script principal
└── requirements.txt               # Dependencias
```

### Estructura de Datasets

```
processors/datasets/saved_datasets/facebook/
└── {run_id}/
    ├── {run_id}.csv              # Metadatos tabulares
    ├── {run_id}.jsonl            # Datos estructurados
    ├── metadata.json             # Info del scraping
    ├── media/                    # Archivos multimedia
    │   ├── imagen1.jpg
    │   ├── video1.mp4
    │   └── ...
    ├── video_frames/             # Frames extraídos
    │   └── ...
    └── reports/                  # Reportes generados
        ├── Reporte_Analisis_Completo_{run_id}.pdf
        └── {run_id}_analysis_complete.json
```

## 🔌 Patrones de Diseño

### 1. Patrón de Módulos (Modular Architecture)

**Implementación**: Routers separados por funcionalidad

```python
# api_service/app/api/routes/apify/facebook/__init__.py
router = APIRouter()

# Incluir sub-routers
router.include_router(scraper_router)
router.include_router(runs_router)
router.include_router(analysis_router)
router.include_router(local_analysis_router)
```

**Ventajas**:
- Separación de responsabilidades
- Mantenibilidad
- Escalabilidad
- Reutilización de código

### 2. Patrón de Servicios (Service Layer)

**Implementación**: Servicios dedicados para operaciones complejas

```python
# services/apify_service.py
class ApifyService:
    async def scrape_facebook_ads(self, params):
        # Lógica de scraping
        pass

# services/pdf_generator.py
class PDFGenerator:
    def generate(self, data):
        # Lógica de generación PDF
        pass
```

**Ventajas**:
- Lógica de negocio centralizada
- Fácil testing
- Reutilización entre endpoints

### 3. Patrón de Procesadores (Processor Pattern)

**Implementación**: Procesadores especializados por tipo de dato

```python
# processors/video_processor/frame_extractor.py
class FrameExtractor:
    def extract_frames(self, video_path):
        # Extracción de frames
        pass

# processors/media_preparation/image_optimizer.py
class ImageOptimizer:
    def optimize(self, image_path):
        # Optimización de imágenes
        pass
```

**Ventajas**:
- Especialización por tipo de dato
- Fácil extensión
- Testing independiente

### 4. Patrón RORO (Receive an Object, Return an Object)

**Implementación**: Funciones que reciben y retornan diccionarios

```python
async def analyze_campaign(params: dict) -> dict:
    """
    Recibe: dict con parámetros
    Retorna: dict con resultados
    """
    # Procesamiento
    return {
        "status": "success",
        "run_id": run_id,
        "pdf_path": pdf_path
    }
```

**Ventajas**:
- Interfaz consistente
- Fácil composición
- Documentación clara

## 🔄 Comunicación entre Componentes

### API ↔ Frontend

**Protocolo**: HTTP/HTTPS REST

**Formato**: JSON

```javascript
// Frontend → API
fetch('http://localhost:8001/api/v1/apify/facebook/analyze-url-with-download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: '...', count: 100 })
})

// API → Frontend
{
    "status": "success",
    "run_id": "...",
    "pdf_path": "..."
}
```

### API ↔ Apify

**Protocolo**: HTTP REST (Apify Client SDK)

**Autenticación**: Token API

```python
from apify_client import ApifyClient

client = ApifyClient(token=APIFY_TOKEN)
run = client.actor(ACTOR_ID).call(input_data)
```

### API ↔ OpenAI

**Protocolo**: HTTPS REST (OpenAI SDK)

**Autenticación**: API Key

**Formato**: JSON con Base64 para imágenes

```python
response = await openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    response_format={"type": "json_object"}
)
```

## 🗄️ Gestión de Estado

### Estado Transitorio

**Almacenamiento en memoria**:
- Variables de configuración
- Clientes de API (Apify, OpenAI)
- Cache de prompts

### Estado Persistente

**Sistema de archivos local**:
- Datasets completos
- Archivos multimedia
- Reportes generados
- Configuraciones

**Sin base de datos**:
- El sistema no requiere base de datos relacional
- Todo se almacena en sistema de archivos
- Facilita portabilidad y backup

## 🔐 Seguridad

### Autenticación

**APIs Externas**:
- Apify: Token en variable de entorno
- OpenAI: API Key en variable de entorno

**API Interna**:
- Actualmente sin autenticación (desarrollo)
- CORS configurado para orígenes específicos

### Manejo de Secretos

```python
# Variables de entorno
APIFY_TOKEN=xxx        # Nunca en código
OPENAI_API_KEY=xxx     # Nunca en código
```

**Carga segura**:
```python
from app.config.env_loader import load_env

load_env()  # Carga desde .env sin commitear
```

### CORS (Cross-Origin Resource Sharing)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",  # Frontend
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📊 Manejo de Concurrencia

### Async/Await

**FastAPI nativo**: Soporte asíncrono completo

```python
@router.post("/analyze-url")
async def analyze_url(request: Request):
    # Operaciones async
    result = await process_async()
    return result
```

**Ventajas**:
- Manejo eficiente de I/O
- Escalabilidad
- No bloquea el servidor

### Procesamiento Paralelo

**Videos e Imágenes**:
- Procesamiento secuencial por diseño
- Evita sobrecarga de memoria
- Mantiene orden predecible

**Futuro**: Paralelización para grandes volúmenes

## 🧪 Testing y Validación

### Validación de Entrada

**Pydantic Models**:
```python
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    url: str
    count: int = 100
    timeout: int = 600
```

**Validación automática**:
- Tipos de datos
- Rangos de valores
- Campos requeridos

### Manejo de Errores

**Estrategia de capas**:
1. Validación de entrada (Pydantic)
2. Validación de negocio (código)
3. Manejo de excepciones (try/except)
4. Respuestas HTTP apropiadas

```python
try:
    result = await process()
except HTTPException:
    raise  # Re-lanzar excepciones HTTP
except Exception as e:
    logger.error(f"Error: {e}")
    raise HTTPException(500, detail=str(e))
```

## 📈 Escalabilidad

### Horizontal

**Limitaciones actuales**:
- Sistema de archivos local
- Sin base de datos compartida
- Procesamiento en un servidor

**Mejoras futuras**:
- Base de datos compartida (PostgreSQL)
- Queue system (Celery, Redis)
- Load balancing
- Contenedores (Docker)

### Vertical

**Optimizaciones implementadas**:
- Procesamiento asíncrono
- Optimización de imágenes
- Límites de procesamiento (50 assets)
- Reutilización de frames

## 🔄 Logging y Monitoreo

### Sistema de Logging

```python
import logging

logger = logging.getLogger("ads_analyzer")

logger.info("Proceso iniciado")
logger.warning("Advertencia")
logger.error("Error encontrado")
```

### Niveles de Logging

- **INFO**: Proceso normal
- **WARNING**: Advertencias no críticas
- **ERROR**: Errores que requieren atención
- **DEBUG**: Información detallada para debugging

### Estructura de Logs

```
[API] 2025-11-24 10:30:00 INFO [module.function] Mensaje
[FRONTEND] 2025-11-24 10:30:01 INFO Mensaje
```

## 🔧 Configuración

### Variables de Entorno

```env
# APIs Externas
APIFY_TOKEN=xxx
OPENAI_API_KEY=xxx

# Configuración
PROMPT="..."
PROMPT_FILE=prompt.txt

# Servidores
API_PORT=8001
FRONTEND_PORT=3001
API_HOST=0.0.0.0
```

### Carga de Configuración

```python
# app/config/env_loader.py
def load_env():
    from dotenv import load_dotenv
    load_dotenv()
```

## 🚀 Inicio del Sistema

### Script Principal

```python
# start.py
python start.py              # Ambos servidores
python start.py --api-only   # Solo API
python start.py --frontend-only  # Solo Frontend
```

### Procesos Iniciados

1. **API Server** (Puerto 8001)
   - FastAPI con Uvicorn
   - Auto-reload en desarrollo
   - Documentación en /docs

2. **Frontend Server** (Puerto 3001)
   - HTTP Server simple
   - Sirve archivos estáticos
   - Sin compilación necesaria

### Manejo de Procesos

- **Threading**: Lectura de output en paralelo
- **Signal Handling**: CTRL+C cierra ambos servidores
- **Auto-restart**: Reinicia si falla (con límites)

## 🔍 Dependencias Principales

### Backend

```
fastapi>=0.104.0          # Framework web
uvicorn>=0.24.0           # Servidor ASGI
apify-client>=1.7.1       # Cliente Apify
openai>=1.0.0             # Cliente OpenAI
pillow>=10.1.0            # Procesamiento imágenes
opencv-python>=4.8.0      # Procesamiento video
reportlab>=4.0.0          # Generación PDF
pandas>=2.1.0             # Manipulación datos
pydantic>=2.0.0           # Validación datos
python-dotenv>=1.0.0      # Variables entorno
```

### Frontend

```
# Sin dependencias npm
# Usa CDN para:
- Lucide Icons
- Google Fonts (Outfit)
```

## 🎯 Decisiones Arquitectónicas Clave

### 1. FastAPI sobre Django REST

**Razón**: Mejor performance, async nativo, documentación automática

### 2. Sistema de Archivos sobre Base de Datos

**Razón**: Simplicidad, portabilidad, fácil backup

### 3. Base64 sobre URLs Públicas

**Razón**: Seguridad, confiabilidad, simplicidad

### 4. Modular sobre Monolítico

**Razón**: Mantenibilidad, escalabilidad, testing

### 5. Async/Await sobre Síncrono

**Razón**: Performance, escalabilidad, mejor UX

## 📊 Métricas de Performance

### Tiempos Típicos

| Operación | Tiempo |
|-----------|--------|
| Scraping (100 anuncios) | 3-5 min |
| Descarga multimedia | 1-2 min |
| Procesamiento videos | 30-60 seg |
| Procesamiento imágenes | 30-60 seg |
| Análisis OpenAI | 30-90 seg |
| Generación PDF | 5-10 seg |
| **Total (URL)** | **5-10 min** |
| **Total (Run ID)** | **2-5 min** |

### Recursos Utilizados

- **CPU**: Moderado (procesamiento de imágenes)
- **RAM**: 500MB - 2GB (depende de cantidad de imágenes)
- **Disco**: Variable (depende de datasets)
- **Red**: Moderado (APIs externas)

## 🔮 Futuras Mejoras Arquitectónicas

### Corto Plazo

1. **Base de datos**: PostgreSQL para metadatos
2. **Cache**: Redis para resultados frecuentes
3. **Queue**: Celery para tareas asíncronas
4. **Autenticación**: JWT tokens

### Mediano Plazo

1. **Microservicios**: Separar scraping, análisis, PDF
2. **Contenedores**: Docker para deployment
3. **Orquestación**: Kubernetes para escalabilidad
4. **Monitoreo**: Prometheus + Grafana

### Largo Plazo

1. **Multi-tenant**: Soporte para múltiples usuarios
2. **CDN**: Para servir multimedia
3. **Event-driven**: Kafka para eventos
4. **Machine Learning**: Modelos propios entrenados

---

**Última actualización**: Noviembre 2025

