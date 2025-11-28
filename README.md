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
const API_BASE = "http://localhost:8001";
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

## 🔬 Procesamiento Avanzado de Datos e IA

Esta sección explica en detalle cómo el sistema procesa, analiza y compara anuncios para generar reportes profesionales de alta calidad.

### 📊 Flujo Completo de Procesamiento

El sistema sigue un pipeline de 7 pasos optimizado y validado:

```
1. SCRAPING → 2. VALIDACIÓN → 3. DETECCIÓN MULTIMEDIA → 4. EXTRACCIÓN →
5. OPTIMIZACIÓN → 6. ENVÍO IA → 7. GENERACIÓN REPORTE
```

#### **PASO 1: Scraping con Apify**

- **Conecta automáticamente** a Facebook Ads Library mediante Apify
- **Descarga datasets completos** incluyendo metadatos (CSV/JSONL) y multimedia
- **Organiza por Run ID** único para trazabilidad completa
- **Validación automática** de integridad de archivos descargados

#### **PASO 2: Validación y Preparación**

- **Verificación de integridad**: Comprueba que todos los archivos necesarios existan
- **Re-descarga inteligente**: Si faltan archivos, los descarga automáticamente desde Apify
- **Estructura de directorios**: Organiza datasets en formato estandarizado:
  ```
  datasets/facebook/{run_id}/
  ├── {run_id}.csv           # Metadatos de anuncios
  ├── {run_id}.jsonl         # Datos estructurados
  ├── media/                 # Imágenes y videos originales
  ├── video_frames/          # Frames extraídos (si aplica)
  └── reports/               # Reportes generados
  ```

### 🎬 Detección y Procesamiento de Videos

El sistema implementa un **sistema de detección multi-capa** para identificar videos de forma robusta:

#### **Detección en 3 Niveles**

**Nivel 1: Detección por Extensión**

- Soporta **8 formatos de video**: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, `.m4v`, `.flv`, `.wmv`
- Identificación rápida por extensión de archivo

**Nivel 2: Detección por Tamaño**

- Si no se encuentran por extensión, busca archivos grandes (>100KB)
- Excluye formatos de imagen conocidos (`.jpg`, `.png`, `.gif`, `.webp`, `.bmp`)
- Identifica potenciales videos por tamaño y tipo desconocido

**Nivel 3: Validación con OpenCV**

- **Verificación técnica profunda**: Abre cada archivo potencial con OpenCV
- **Validación de propiedades**:
  - Verifica que el archivo se pueda abrir correctamente
  - Comprueba que tenga frames (`frame_count > 0`)
  - Valida FPS válido (`fps > 0`)
  - Rechaza archivos corruptos o incompletos
- **Zero False Positives**: Solo archivos que OpenCV puede procesar son considerados videos válidos

#### **Extracción Inteligente de Frames**

El sistema extrae frames de forma **estratégica y distribuida**:

1. **Distribución temporal**: Los frames se extraen de puntos distribuidos a lo largo del video

   - No solo al inicio (evita solo mostrar el primer segundo)
   - Distribución equitativa (1/4, 1/2, 3/4 del video)
   - Captura la evolución narrativa del anuncio

2. **Cálculo dinámico**:

   - Calcula cuántos frames extraer por video según el total disponible
   - Distribuye equitativamente entre todos los videos encontrados
   - Respeta el límite del 40% del total de media

3. **Optimización de calidad**:
   - Redimensiona frames muy grandes (>1920px) para optimizar transferencia
   - Usa interpolación LANCZOS4 para mantener calidad visual
   - Guarda en JPEG calidad 85 (balance calidad/tamaño)
   - Conserva frames para reutilización posterior

**Ejemplo de extracción:**

```
Video de 100 frames, 3 frames a extraer:
- Frame 25 (25% del video)
- Frame 50 (50% del video)
- Frame 75 (75% del video)
```

#### **Gestión Inteligente de Frames**

- **Reutilización**: Si ya existen frames extraídos, los reutiliza (evita reprocesamiento)
- **Validación continua**: Verifica que los frames extraídos sean imágenes válidas
- **Manejo de errores**: Si un video falla, continúa con los siguientes sin detener el proceso
- **Logging detallado**: Registra cada paso para debugging y auditoría

### 🖼️ Procesamiento de Imágenes Estáticas

#### **Detección y Filtrado**

1. **Identificación por extensión**: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.bmp`
2. **Exclusión de videos**: Filtra explícitamente extensiones de video para evitar duplicados
3. **Validación de integridad**: Usa `PIL.Image.verify()` para validar que sean imágenes válidas
4. **Ordenamiento inteligente**: Ordena por tamaño de archivo (prioriza imágenes de mayor calidad)

#### **Optimización para OpenAI**

Cada imagen se procesa antes de enviar:

1. **Conversión de formato**:

   - Convierte formatos especiales (RGBA, P, LA) a RGB estándar
   - Asegura compatibilidad universal

2. **Redimensionamiento inteligente**:

   - Si la imagen es muy grande (>800px en cualquier dimensión), la redimensiona
   - Mantiene aspect ratio con algoritmo LANCZOS (alta calidad)
   - Reduce tamaño de archivo sin perder información crítica

3. **Compresión optimizada**:
   - Guarda en JPEG calidad 85 (balance perfecto calidad/tamaño)
   - Habilita optimización automática
   - Reduce transferencia de datos y costos de API

### ⚖️ Balance 40/60: Videos vs Imágenes

El sistema implementa un **balance científico** basado en mejores prácticas de análisis de anuncios:

#### **Proporción Optimizada**

- **40% Frames de Video** (20 de 50 total): Captura narrativa, movimiento, storytelling
- **60% Imágenes Estáticas** (30 de 50 total): Análisis detallado de composición, diseño, texto

**¿Por qué esta proporción?**

1. **Videos requieren más contexto**: Cada frame de video muestra un momento de la narrativa, pero necesita más frames para entender la historia completa
2. **Imágenes estáticas son más densas en información**: Una imagen puede ser analizada completamente en un solo frame
3. **Balance de análisis**: Permite comparar narrativas dinámicas (videos) con diseño estático (imágenes)
4. **Optimización de tokens**: Respeta límites de OpenAI mientras maximiza información

#### **Implementación Dinámica**

El sistema ajusta automáticamente la proporción:

```python
MAX_IMAGES = 50                    # Total máximo de assets
max_static_images = 30             # 60% = 30 imágenes estáticas
max_video_frames = 20              # 40% = 20 frames de video

# Si se procesan menos frames de video de los esperados:
if total_video_frames < max_video_frames:
    # Ajusta el límite de imágenes estáticas para usar todos los slots
    remaining_slots = MAX_IMAGES - total_video_frames
    max_static_images = remaining_slots
```

**Validación de balance:**

- Calcula porcentaje final de frames vs imágenes
- Registra advertencias si el balance no se cumple
- Genera logs detallados para auditoría

### 📤 Codificación Base64 y Envío a OpenAI

#### **Codificación Base64**

**¿Por qué Base64 en lugar de URLs?**

1. **Seguridad**: Los datos nunca salen del servidor
2. **Confiabilidad**: No depende de servidores externos (ngrok, etc.)
3. **Velocidad**: Elimina latencia de descarga de imágenes
4. **Compatibilidad**: Funciona siempre, incluso en entornos aislados

**Proceso de codificación:**

```python
# 1. Cargar imagen optimizada
img = Image.open(image_file)

# 2. Redimensionar si es necesario
if max(img.size) > 800:
    img.thumbnail((800, 800), Image.Resampling.LANCZOS)

# 3. Convertir a bytes en memoria
buffered = BytesIO()
img.save(buffered, format="JPEG", quality=85, optimize=True)

# 4. Codificar a Base64
b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

# 5. Crear URL data para OpenAI
data_url = f"data:image/jpeg;base64,{b64}"
```

#### **Estructura del Payload para OpenAI**

El sistema construye un payload **estructurado y optimizado**:

```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "system",
      "content": "Eres un experto analista de marketing digital..."
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "[Información del dataset + Prompt personalizado]"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,...",
            "detail": "high"
          }
        }
        // ... más imágenes y frames
      ]
    }
  ],
  "response_format": { "type": "json_object" }
}
```

**Características clave:**

- **Modo de alta resolución**: `"detail": "high"` permite análisis detallado
- **Formato JSON forzado**: Garantiza respuesta estructurada
- **Sin límite de tokens**: Permite respuestas completas y detalladas
- **Contexto estructurado**: Combina información del dataset con el prompt personalizado

### 🧠 Sistema de Prompts Personalizables

El sistema implementa un **sistema de prompts flexible y profesional**:

#### **Jerarquía de Carga de Prompts**

1. **Variable de entorno `PROMPT`** (Prioridad 1)

   - Permite cambiar el prompt sin modificar código
   - Útil para pruebas y personalización rápida

2. **Archivo definido en `PROMPT_FILE`** (Prioridad 2)

   - Por defecto busca `prompt.txt` en la raíz
   - Permite prompts complejos y extensos
   - Fácil de versionar y compartir

3. **`DEFAULT_PROMPT` del módulo** (Prioridad 3)

   - Prompt profesional pre-configurado
   - Incluye criterios de evaluación estructurados
   - Garantiza calidad mínima

4. **Prompt básico de emergencia** (Prioridad 4)
   - Solo si fallan todas las opciones anteriores

#### **Estructura del Prompt Estándar**

El prompt incluye instrucciones para generar:

1. **Metadata del reporte**:

   - Rol del analista generado
   - Marca detectada
   - Métricas usadas para ranking
   - Tamaño de muestra

2. **Resumen ejecutivo**:

   - Overview de performance (mínimo 200 palabras)
   - Patrones de éxito comunes
   - Conclusiones estratégicas

3. **Análisis top 10**:

   - Ranking detallado
   - Métricas de cada anuncio
   - Forensic breakdown (hook, audio, narrativa)
   - Scores de expertos (visual, storytelling, brand, conversión)
   - Takeaways clave

4. **Recomendaciones estratégicas**:
   - Recomendaciones detalladas y accionables
   - Priorización de mejoras
   - Roadmap de optimización

#### **Contexto Adicional Incluido**

El sistema añade automáticamente al prompt:

```python
dataset_info = f"""
INFORMACIÓN DEL DATASET:
- Run ID: {run_id}
- Total de anuncios: {len(df)}
- Imágenes estáticas: {max_static_images}
- Frames de video: {max_video_frames}
- Total multimedia: {MAX_IMAGES}

INSTRUCCIÓN CRÍTICA:
- Debes retornar ÚNICAMENTE un objeto JSON válido
- TODO en ESPAÑOL
- Análisis PROFUNDO y DETALLADO
- Contrasta imágenes estáticas con frames de video
"""
```

Esto asegura que la IA:

- Sepa exactamente cuántos anuncios analizar
- Entienda el balance de media procesada
- Genere análisis contrastando videos e imágenes
- Retorne formato JSON válido para generación de PDF

### 🔄 Comparación Videos vs Imágenes

El sistema está diseñado para que la IA **compare y contraste** ambos tipos de media:

#### **Análisis Comparativo Automático**

La IA recibe instrucciones explícitas para:

1. **Identificar diferencias narrativas**:

   - Videos: Storytelling, evolución temporal, hooks dinámicos
   - Imágenes: Diseño estático, composición, impacto instantáneo

2. **Evaluar efectividad por formato**:

   - Videos: Engagement, retención, cierre narrativo
   - Imágenes: Stopping power, claridad de mensaje, call-to-action

3. **Recomendaciones específicas**:
   - Qué funciona mejor en video vs imagen
   - Cuándo usar cada formato
   - Cómo optimizar cada tipo de creativo

#### **Ventajas del Balance 40/60**

- **Perspectiva completa**: No se pierde información de ningún tipo de creativo
- **Análisis profundo**: Suficiente contexto de videos (40%) para entender narrativas
- **Eficiencia**: Máximo de imágenes estáticas (60%) para análisis detallado de diseño
- **Representatividad**: Refleja la realidad del ecosistema de anuncios (mix de formatos)

### ✅ Validación y Control de Calidad

El sistema implementa **múltiples capas de validación**:

#### **Validación Pre-Envío**

1. **Validación de payload**:

   - Verifica que haya al menos texto e imágenes
   - Valida formato JSON del contenido
   - Comprueba que los bloques Base64 sean válidos

2. **Validación de balance**:

   - Confirma que se procesó el porcentaje esperado de frames
   - Alerta si hay desbalance significativo
   - Ajusta límites dinámicamente

3. **Validación de tamaño**:
   - Verifica que no se excedan límites de OpenAI
   - Optimiza imágenes antes de enviar
   - Calcula tokens estimados

#### **Validación Post-Respuesta**

1. **Verificación de rechazo**:

   - Detecta si OpenAI rechazó la solicitud
   - Identifica respuestas vacías
   - Guarda respuestas rechazadas para análisis

2. **Validación de JSON**:

   - Intenta parsear JSON estándar
   - Si falla, usa `json_repair` para corregir
   - Valida estructura esperada

3. **Validación de contenido**:
   - Verifica que todos los campos requeridos existan
   - Comprueba que los scores estén en rango válido
   - Valida longitud mínima de textos descriptivos

#### **Logging y Auditoría**

Todo el proceso es **completamente trazable**:

- Logs detallados en cada paso
- Métricas de procesamiento (tiempos, tamaños, cantidades)
- Estadísticas de balance final
- Errores capturados con tracebacks completos
- Archivos de debugging guardados automáticamente

### 🎯 Beneficios del Sistema de Procesamiento

1. **Robustez**: Maneja errores sin detenerse, valida cada paso
2. **Eficiencia**: Optimiza imágenes, reutiliza frames, minimiza transferencias
3. **Precisión**: Detección multi-capa evita falsos positivos
4. **Flexibilidad**: Prompts personalizables, balance ajustable
5. **Trazabilidad**: Logging completo para debugging y auditoría
6. **Escalabilidad**: Procesa cualquier cantidad de anuncios eficientemente

### 📈 Métricas y Rendimiento

El sistema proporciona métricas detalladas:

- **Tokens utilizados**: Rastreo de costo de API
- **Tiempo de procesamiento**: Por cada etapa
- **Balance final**: Porcentaje real de frames vs imágenes
- **Tasa de éxito**: Porcentaje de assets procesados exitosamente
- **Tamaño de payload**: Optimización verificada

Estas métricas permiten:

- Optimizar costos
- Identificar cuellos de botella
- Validar calidad del procesamiento
- Mejorar continuamente el sistema

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
