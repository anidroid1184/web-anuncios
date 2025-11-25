# 📊 Analizador de Anuncios de Facebook - Documentación Completa

Sistema completo de análisis de anuncios de Facebook/Meta que integra scraping automatizado con Apify, análisis con IA (OpenAI GPT-4o), generación de reportes PDF profesionales y una interfaz web moderna.

## 🎯 Descripción del Proyecto

Este proyecto permite:

- **Scraping Automatizado**: Extrae anuncios de Facebook Ads Library usando Apify
- **Análisis con IA**: Analiza anuncios usando OpenAI GPT-4o con visión (imágenes y frames de video)
- **Generación de Reportes**: Crea reportes PDF profesionales y detallados
- **Procesamiento de Multimedia**: Maneja imágenes estáticas y videos (extracción de frames)
- **Interfaz Web**: Prototipo frontend para análisis interactivo

## 🏗️ Arquitectura del Sistema

```
web_analizador_anuncios/
├── api_service/                    # Backend FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── apify/
│   │   │           └── facebook/
│   │   │               ├── modules/
│   │   │               │   ├── local_analysis/      # Análisis local con Base64
│   │   │               │   ├── campaign_analysis/   # Análisis de campañas completo
│   │   │               │   ├── scraper.py           # Scraping con Apify
│   │   │               │   └── utils.py
│   │   │               └── __init__.py
│   │   ├── processors/
│   │   │   ├── datasets/
│   │   │   │   └── saved_datasets/facebook/    # Datasets descargados
│   │   │   └── facebook/
│   │   │       └── extract_dataset.py          # Descarga de datasets
│   │   └── main.py
│   └── main.py                    # Punto de entrada FastAPI
├── frontend/
│   └── prototype/                 # Frontend simple (HTML/JS)
│       ├── index.html
│       ├── script.js              # Lógica del frontend
│       └── style.css
├── frontend_server.py             # Servidor HTTP para frontend
├── start.py                       # Script principal para iniciar ambos servidores
├── scripts/                       # Scripts de inicio individuales
│   ├── start-api.py
│   ├── start-frontend.py
│   └── *.ps1, *.sh               # Scripts para diferentes OS
└── README.md                      # Este archivo
```

## 🚀 Inicio Rápido

### Prerrequisitos

1. **Python 3.9+**
2. **Variables de entorno** (ver `.env.example`):
   - `APIFY_TOKEN`: Token de Apify para scraping
   - `OPENAI_API_KEY`: Clave API de OpenAI para análisis con IA
   - `PROMPT` o `PROMPT_FILE`: (Opcional) Prompt personalizado para OpenAI

### Instalación

```bash
# Clonar el repositorio
git clone <repository-url>
cd web_analizador_anuncios

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Ejecución

**Método recomendado** (inicia ambos servidores en una terminal):

```bash
python start.py
```

Esto iniciará:
- **API Server** en `http://localhost:8001`
- **Frontend Server** en `http://localhost:3001`
- **API Docs** (Swagger) en `http://localhost:8001/docs`

Los logs se mostrarán con prefijos `[API]` y `[FRONTEND]` para fácil identificación.

**Opciones de inicio:**

```bash
python start.py --api-only      # Solo API
python start.py --frontend-only # Solo Frontend
```

**Inicio individual:**

```bash
# API solamente
python scripts/start-api.py

# Frontend solamente  
python scripts/start-frontend.py
```

## 📡 Endpoints de la API

### 🔗 Endpoints Usados por el Frontend

El frontend (`frontend/prototype/`) utiliza los siguientes endpoints principales:

#### 1. **Análisis desde URL** (Modo URL)
```http
POST /api/v1/apify/facebook/analyze-url-with-download
Content-Type: application/json

{
  "url": "https://www.facebook.com/ads/library/?active_status=active&...",
  "count": 100,
  "timeout": 600
}
```

**Qué hace:**
- Conecta a Apify y crea un nuevo dataset
- Descarga el dataset si no existe localmente
- Extrae frames de videos (40% del total de media)
- Procesa imágenes estáticas (60% del total)
- Envía todo a OpenAI GPT-4o con Base64
- Genera reporte PDF profesional
- Retorna paths al PDF y JSON

**Respuesta:**
```json
{
  "status": "success",
  "run_id": "abc123",
  "pdf_path": "/path/to/reporte.pdf",
  "json_report": "/path/to/reporte.json"
}
```

#### 2. **Análisis desde Run ID** (Modo Run ID)
```http
POST /api/v1/apify/facebook/analyze-local-and-pdf?run_id={run_id}
```

**Qué hace:**
- Usa un dataset ya descargado localmente
- Extrae frames de videos si existen
- Procesa imágenes estáticas
- Envía a OpenAI con Base64
- Genera reporte PDF
- Retorna paths al PDF y JSON

#### 3. **Descarga de PDF**
```http
GET /api/v1/apify/facebook/pdf/{run_id}
```

Retorna el PDF generado como descarga directa.

---

### 🔧 Otros Endpoints Disponibles

#### **Scraping y Gestión de Datasets**

```http
POST /api/v1/apify/facebook/scrape-and-save
```
Inicia scraping y descarga automática del dataset.

```http
GET /api/v1/apify/facebook/runs/list
```
Lista todos los runs locales guardados.

```http
GET /api/v1/apify/facebook/runs/{run_id}
```
Obtiene información de un run específico.

```http
POST /api/v1/apify/facebook/download-dataset-from-run
Body: { "run_id": "...", "download_media": true }
```
Descarga un dataset desde Apify si no existe localmente.

#### **Análisis de Campañas** (Endpoints avanzados)

```http
POST /api/v1/apify/facebook/analyze-url
```
Análisis completo de campaña desde URL (similar a `analyze-url-with-download` pero con estructura diferente).

#### **Archivos Estáticos**

```http
GET /api/v1/apify/facebook/saved/{run_id}/reports/{filename}
```
Sirve archivos estáticos desde el directorio de reports.

---

### 📚 Documentación Interactiva

Una vez iniciado el servidor, visita:

- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

Aquí puedes ver todos los endpoints, sus parámetros, ejemplos y probarlos directamente.

## 🎨 Frontend

### Estructura

```
frontend/prototype/
├── index.html    # HTML principal con formulario
├── script.js     # Lógica JavaScript (llamadas API)
└── style.css     # Estilos
```

### Funcionalidades

1. **Selector de Modo**:
   - **URL**: Analiza desde una URL de Facebook Ads Library
   - **Run ID**: Analiza desde un dataset ya descargado

2. **Formulario de Análisis**:
   - Input dinámico según el modo seleccionado
   - Validación de entrada
   - Estados de carga (botón deshabilitado, texto cambiante)

3. **Descarga Automática**:
   - El PDF se descarga automáticamente al completar el análisis

4. **Resultados**:
   - Muestra Run ID
   - Links a PDF y JSON
   - Mensajes de éxito/error

### Personalización del Frontend

**Modificar el endpoint base:**

En `frontend/prototype/script.js`, línea 26:
```javascript
const API_BASE = 'http://localhost:8001';
```

**Modificar estilos:**

Edita `frontend/prototype/style.css` para cambiar colores, fuentes, layout, etc.

**Agregar nuevos campos:**

1. Agrega el campo HTML en `index.html`
2. Actualiza `script.js` para leer el valor del campo
3. Inclúyelo en el body de la petición fetch

## 🔧 Cómo Modificar el Proyecto

### Agregar un Nuevo Endpoint

1. **Crear el endpoint en el módulo correspondiente:**

```python
# api_service/app/api/routes/apify/facebook/modules/tu_modulo/endpoints.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/tu-modulo", tags=["tu-tag"])

class TuRequest(BaseModel):
    campo1: str
    campo2: int

@router.post("/tu-endpoint")
async def tu_endpoint(request: TuRequest):
    try:
        # Tu lógica aquí
        return {"status": "success", "data": "..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

2. **Registrar el router en `__init__.py`:**

```python
# api_service/app/api/routes/apify/facebook/__init__.py

from app.api.routes.apify.facebook.modules.tu_modulo.endpoints import router as tu_router

# En la función que registra los routers:
router.include_router(tu_router)
```

3. **Reiniciar el servidor** (el servidor se recarga automáticamente con WatchFiles)

### Modificar el Procesamiento de Videos/Imágenes

**Archivo clave:** `api_service/app/api/routes/apify/facebook/modules/local_analysis/endpoints.py`

**Secciones importantes:**

1. **Detección de videos** (línea ~527):
   - Modifica `video_extensions` para agregar nuevos formatos
   - Ajusta la función `is_valid_video_file()` para validación personalizada

2. **Extracción de frames** (línea ~550):
   - Cambia `num_frames_to_extract` para más/menos frames
   - Modifica la distribución de frames en el video

3. **Proporción de media** (línea ~614):
   ```python
   MAX_IMAGES = 50  # Total máximo
   max_static_images = int(MAX_IMAGES * 0.6)  # 60% imágenes
   max_video_frames = int(MAX_IMAGES * 0.4)   # 40% frames
   ```

4. **Procesamiento de imágenes** (línea ~889):
   - Ajusta el tamaño máximo: `img.thumbnail((800, 800), ...)`
   - Cambia calidad JPEG: `quality=85`

### Modificar el Prompt de OpenAI

**Opción 1: Variable de entorno**
```bash
export PROMPT="Tu prompt personalizado aquí"
```

**Opción 2: Archivo**
```bash
export PROMPT_FILE="mi_prompt.txt"
```

Crea `mi_prompt.txt` en la raíz del proyecto con tu prompt.

**Opción 3: Modificar código**

En `endpoints.py`, línea ~622, modifica la carga del prompt o el `DEFAULT_PROMPT`.

### Modificar la Generación de PDFs

**Archivo clave:** 
- `api_service/app/api/routes/apify/facebook/modules/campaign_analysis/pdf_renderer.py`
- `api_service/app/api/routes/apify/facebook/modules/local_analysis/endpoints.py` (línea ~950)

El PDF usa ReportLab. Para modificar:
1. Cambia estilos en `pdf_renderer.py`
2. Ajusta el mapeo de datos JSON a PDF en `endpoints.py`

### Agregar Nuevos Campos al Análisis

1. **Actualizar el prompt** para solicitar el nuevo campo en el JSON
2. **Actualizar el mapeo** en `map_openai_to_pdf_data()` (si existe)
3. **Actualizar el renderer PDF** para mostrar el nuevo campo

## 📦 Estructura de Datos

### Directorio de Datasets

Los datasets se guardan en:
```
api_service/app/processors/datasets/saved_datasets/facebook/{run_id}/
├── {run_id}.csv              # Dataset en CSV
├── {run_id}.jsonl            # Dataset en JSONL
├── media/                    # Imágenes y videos descargados
│   ├── imagen1.jpg
│   ├── video1.mp4
│   └── ...
├── video_frames/             # Frames extraídos de videos
│   ├── video1_frame000.jpg
│   └── ...
└── reports/                  # Reportes generados
    ├── Reporte_Analisis_Completo_{run_id}.pdf
    └── {run_id}_analysis_complete.json
```

### Formato JSON del Análisis

El análisis de OpenAI retorna un JSON con esta estructura (definida en el prompt):

```json
{
  "report_meta": {
    "generated_role": "...",
    "brand_detected": "...",
    "ranking_metric_used": "...",
    "sample_size": "..."
  },
  "executive_summary": {
    "performance_overview": "...",
    "common_success_patterns": "..."
  },
  "top_10_analysis": [...],
  "strategic_recommendations": [...]
}
```

## 🔍 Debugging

### Logs

Los logs se muestran en la terminal con prefijos:
- `[API]`: Logs del servidor FastAPI
- `[FRONTEND]`: Logs del servidor frontend

### Logs Detallados del Análisis

El endpoint de análisis genera logs detallados:
- Progreso de scraping
- Detección de videos
- Extracción de frames
- Procesamiento de imágenes
- Llamada a OpenAI
- Generación de PDF

### Verificar Datasets

```bash
# Listar runs locales
curl http://localhost:8001/api/v1/apify/facebook/runs/list

# Ver contenido de un run
ls -la api_service/app/processors/datasets/saved_datasets/facebook/{run_id}/
```

### Problemas Comunes

1. **"No se encontraron videos"**:
   - Verifica que los videos se descargaron en `media/`
   - Revisa las extensiones de video soportadas
   - Verifica que OpenCV esté instalado: `pip install opencv-python`

2. **"OpenAI rechazó la solicitud"**:
   - Revisa el prompt (puede violar políticas de OpenAI)
   - Verifica que las imágenes estén en formato válido
   - Revisa logs para ver la respuesta exacta

3. **"0 frames de video procesados"**:
   - Verifica que los videos existan en `media/`
   - Revisa logs de extracción de frames
   - Asegúrate de que OpenCV pueda leer los videos

## 🛠️ Tecnologías Utilizadas

- **Backend**: FastAPI (Python)
- **Frontend**: HTML/CSS/JavaScript (Vanilla)
- **Scraping**: Apify Client
- **IA**: OpenAI GPT-4o (con visión)
- **PDFs**: ReportLab
- **Imágenes**: Pillow (PIL)
- **Videos**: OpenCV (cv2)
- **Servidor**: Uvicorn (ASGI)

## 📝 Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Apify
APIFY_TOKEN=tu_token_aqui

# OpenAI
OPENAI_API_KEY=tu_api_key_aqui

# Opcional: Prompt personalizado
PROMPT="Tu prompt aquí"
# O usar archivo:
PROMPT_FILE=prompt.txt

# Configuración del servidor
API_PORT=8001
FRONTEND_PORT=3001
```

## 🚨 Solución de Problemas

### El servidor no inicia

- Verifica que los puertos 8001 y 3001 estén libres
- Revisa las variables de entorno
- Verifica que todas las dependencias estén instaladas

### El análisis falla

- Revisa los logs en la terminal
- Verifica que Apify token sea válido
- Verifica que OpenAI API key sea válida
- Revisa que el dataset se haya descargado correctamente

### El PDF no se genera

- Verifica que el análisis haya completado exitosamente
- Revisa el directorio `reports/` del run
- Verifica que ReportLab esté instalado




**Última actualización**: Noviembre 2025

Para más detalles, consulta la documentación interactiva en `http://localhost:8001/docs` cuando el servidor esté corriendo.
