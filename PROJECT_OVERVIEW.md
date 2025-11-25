# 📊 Analizador de Anuncios - Proyecto Completo

## 🎯 Descripción General

Sistema integral de análisis de publicidad digital que automatiza la recopilación, procesamiento y análisis de anuncios de redes sociales (Facebook, Instagram, TikTok) mediante scraping con Apify, procesamiento de multimedia y análisis con IA (OpenAI GPT-4).

---

## 📖 RESUMEN EJECUTIVO PARA CONTEXTO RÁPIDO

### ¿Qué hace este sistema?

**En una frase:** Extrae anuncios de Facebook/Instagram/TikTok, descarga sus imágenes y videos, y los analiza con IA para determinar cuál es el mejor anuncio y por qué, generando reportes automáticos con rankings y recomendaciones de optimización.

### ¿Cómo funciona el proceso completo?

**Imagina que eres un marketero que quiere analizar la competencia:**

1. **Le dices al sistema:** "Busca anuncios de Nike sobre zapatos en Estados Unidos"
2. **El sistema automáticamente:**
   - 🔍 Busca en Facebook Ad Library usando Apify (servicio de scraping)
   - 📥 Descarga todas las imágenes y videos de los anuncios encontrados
   - 🎬 Si hay videos, extrae 3 capturas (inicio, medio, fin) para analizarlas
   - 🤖 Envía todo a OpenAI GPT-4 con un prompt especializado que pregunta:
     - "¿Qué elementos visuales tiene cada anuncio?"
     - "¿Qué gatillos psicológicos usa (escasez, prueba social, urgencia)?"
     - "¿Qué tan efectivo es el call-to-action?"
     - "¿Cuál anuncio es el GANADOR y por qué?"
   - 📊 Genera un reporte que muestra:
     - **🥇 GANADOR:** Ad #123456 con score 9.2/10 porque...
     - **🥈 Segundo lugar:** Ad #789012 con score 8.7/10
     - **Tabla completa** de ranking de todos los anuncios
     - **Recomendaciones específicas:** "Cambiar el color del botón a rojo aumentaría el CTR en 15%"

### ¿Para quién es esto?

- **Agencias de marketing:** Analizar campañas de clientes o competencia
- **Marketers:** Optimizar sus propios anuncios basándose en mejores prácticas
- **Equipos de creative:** Entender qué elementos visuales funcionan mejor
- **Analistas:** Hacer benchmarking de industria

### ¿Qué hace diferente a este sistema?

**❌ Otros sistemas:**

- Requieren análisis manual de cada anuncio
- No comparan múltiples anuncios automáticamente
- Solo dan métricas básicas (likes, shares)

**✅ Este sistema:**

- Análisis automático con IA especializada en publicidad
- **Comparación obligatoria:** Siempre dice cuál es el mejor y por qué
- Analiza componentes psicológicos y de diseño que no son visibles en métricas
- Genera reportes listos para presentar a clientes

### ¿Qué tecnología usa por detrás?

- **Scraping:** Apify (plataforma profesional de web scraping)
- **IA:** OpenAI GPT-4o-mini con Vision (puede "ver" imágenes)
- **Videos:** OpenCV para extraer frames automáticamente
- **Backend:** FastAPI (API REST moderna y rápida)
- **Frontend:** Django (dashboard web)
- **Reportes:** JSON + Markdown + PDF

### Caso de uso típico:

```
ENTRADA:
"Quiero analizar anuncios de mi competidor sobre productos de limpieza"

EL SISTEMA HACE:
1. Busca 147 anuncios en Facebook Ad Library
2. Descarga 523 imágenes y 18 videos
3. Extrae 54 frames de los videos
4. Analiza los 10 mejores anuncios con GPT-4
5. Compara todos entre sí

SALIDA:
📄 Reporte que dice:
"El anuncio ganador (#456789) funciona porque:
- Usa colores contrastantes (azul/amarillo)
- Tiene prueba social ('5000+ familias lo usan')
- CTA urgente ('Solo hoy 40% OFF')
- Mujer sonriente genera confianza

Recomendaciones para tus anuncios:
1. ALTA PRIORIDAD: Agregar testimonios de clientes (+15% CTR esperado)
2. MEDIA: Cambiar fondo blanco por color (+8% engagement)
3. BAJA: Probar diferentes tipografías en CTA"
```

### ¿Qué NO hace?

- ❌ No publica anuncios (solo analiza)
- ❌ No accede a cuentas privadas de Facebook Ads
- ❌ No muestra métricas reales (impresiones, conversiones) - solo análisis visual
- ❌ No genera creativos nuevos - solo analiza existentes

### Limitaciones importantes:

1. **Solo anuncios públicos:** Facebook Ad Library solo muestra ads activos públicamente
2. **Costo de IA:** Analizar 10 anuncios cuesta ~$0.50 USD en tokens de OpenAI
3. **Tiempo de procesamiento:** 2-5 minutos para analizar 10 anuncios completos
4. **Requiere buenos prompts:** La calidad del análisis depende del prompt usado

### ¿Cómo se usa?

**Opción 1: API REST**

```bash
# Paso 1: Scrapear
POST /api/v1/apify/facebook/scrape
{"keywords": "Nike shoes"}

# Paso 2: Descargar multimedia
POST /api/v1/apify/facebook/download-media?run_id=abc123

# Paso 3: Analizar y obtener reporte
POST /api/v1/apify/facebook/analyze-and-generate-pdf?run_id=abc123&top_n=10
```

**Opción 2: Dashboard Web**

- Entrar a http://localhost:8002
- Click en "Nueva Campaña"
- Ingresar keywords
- Ver resultados en dashboard

### Archivos clave que genera:

```
reports/
├── abc123_analysis.json      # Datos estructurados (para programas)
├── abc123_analysis.md        # Reporte legible (para humanos)
└── abc123_report.pdf         # Presentación (para clientes)
```

### Ejemplo de output del análisis comparativo:

```markdown
## 🏆 ANÁLISIS COMPARATIVO

### 🥇 GANADOR: Anuncio #829095826733139

**Score Global:** 9.2/10

**Por qué gana:**

- Stopping power excepcional (9.5/10): Imagen de producto en primer plano con fondo difuminado
- CTA ultra claro (9.8/10): "COMPRAR AHORA - 50% OFF HOY"
- Gatillo de escasez activado: "Quedan solo 12 unidades"
- Prueba social: "★★★★★ 2,847 reseñas"

**Fortalezas clave:**

1. Uso de rojo para crear urgencia
2. Precio tachado visible ($199 → $99)
3. Badge de "ENVÍO GRATIS" prominente

### 🥈 SEGUNDO LUGAR: Anuncio #1321488129781413

**Score Global:** 8.7/10

**Por qué está en segundo lugar:**

- Stopping power bueno (8.2/10) pero menos impactante
- CTA menos urgente: "Ver más" vs "Comprar ahora"
- Falta indicador de escasez

**Qué necesita mejorar:**

1. Agregar urgencia temporal ("Oferta termina en 6 horas")
2. Hacer el precio más grande
3. Incluir badge de garantía

### 📊 TABLA COMPLETA DE RANKING

| Rank | Anuncio ID       | Score | Mejor Atributo      |
| ---- | ---------------- | ----- | ------------------- |
| 1    | 829095826733139  | 9.2   | cta_strength        |
| 2    | 1321488129781413 | 8.7   | message_clarity     |
| 3    | 1093933469480670 | 8.3   | emotional_relevance |
| 4    | 1287206829872336 | 7.9   | brand_recall        |
| 5    | 1184303283550089 | 7.5   | stopping_power      |
```

### Arquitectura conceptual simplificada:

```
USUARIO
   ↓
[FRONTEND WEB] ←→ [BACKEND API]
                      ↓
              ┌───────┴──────────┐
              ↓                  ↓
         [APIFY]            [OPENAI]
       (Scraping)         (Análisis IA)
              ↓                  ↓
        [ARCHIVOS]          [REPORTES]
      (imgs/videos)       (JSON/MD/PDF)
```

### Valor del sistema:

**Sin este sistema:**

- ⏰ 4 horas para analizar manualmente 10 anuncios
- 🧠 Análisis subjetivo y inconsistente
- 📊 Sin comparación estructurada
- 💼 Reportes manuales en PowerPoint

**Con este sistema:**

- ⚡ 5 minutos automáticos
- 🤖 Análisis objetivo con criterios consistentes
- 📊 Comparación automática y ranking
- 📄 Reportes generados automáticamente

### Prompt especializado:

El sistema usa un prompt de ~200 líneas que le dice a GPT-4:

> "Eres un experto en marketing digital. Para CADA imagen:
>
> 1. Analiza composición visual (colores, layout, jerarquía)
> 2. Identifica gatillos psicológicos (escasez, autoridad, prueba social)
> 3. Evalúa efectividad del CTA
> 4. Da score de 1-10 en 5 métricas
> 5. **OBLIGATORIO:** Compara TODOS los anuncios y declara un GANADOR con justificación técnica"

---

---

## 🏗️ Arquitectura del Sistema

### Backend (FastAPI)

- **Ubicación:** `api_service/`
- **Puerto:** 8001
- **Framework:** FastAPI + Uvicorn
- **Funcionalidades principales:**
  - API REST para scraping de anuncios
  - Procesamiento de datasets de Apify
  - Análisis con OpenAI Vision API
  - Generación de reportes (JSON, Markdown, PDF)
  - Extracción automática de frames de videos

### Frontend (Django)

- **Ubicación:** `frontend/`
- **Framework:** Django 4.2
- **Interfaz:** Templates HTML + Bootstrap
- **Funcionalidades:**
  - Dashboard de campañas
  - Visualización de análisis
  - Gestión de reportes

---

## 🔄 Flujo de Trabajo Completo

### 1️⃣ **Scraping de Anuncios**

**Endpoint:** `POST /api/v1/apify/facebook/scrape`

**Proceso:**

1. Usuario proporciona parámetros de búsqueda (keywords, país, idioma)
2. Sistema lanza actor de Apify para Facebook Ad Library
3. Apify extrae:
   - Metadata de anuncios
   - URLs de imágenes
   - URLs de videos
   - Textos y CTAs
4. Datos guardados en formato CSV

**Salida:**

```
app/processors/datasets/saved_datasets/facebook/{run_id}/
├── {run_id}.csv          # Datos estructurados
├── metadata.json         # Info del scraping
└── raw_snapshot.json     # Respuesta completa de Apify
```

---

### 2️⃣ **Descarga de Multimedia**

**Endpoint:** `POST /api/v1/apify/facebook/download-media`

**Proceso:**

1. Lee CSV del run_id especificado
2. Descarga imágenes y videos de URLs extraídas
3. Organiza archivos por anuncio

**Estructura generada:**

```
app/processors/datasets/saved_datasets/facebook/{run_id}/
├── media/
│   ├── {ad_id}_image1.jpg
│   ├── {ad_id}_image2.jpg
│   └── {ad_id}_video.mp4
└── video_frames/          # Generado en paso 3
    ├── {ad_id}_frame0.jpg
    ├── {ad_id}_frame1.jpg
    └── {ad_id}_frame2.jpg
```

---

### 3️⃣ **Análisis con OpenAI (Automático)**

**Endpoint:** `POST /api/v1/apify/facebook/analyze-and-generate-pdf`

**Parámetros:**

- `run_id`: ID del dataset descargado
- `top_n`: Número de anuncios a analizar (default: 10)

**Proceso detallado:**

#### Paso 1: Extracción de Frames de Video

```python
# Busca videos en media/
videos = [.mp4, .avi, .mov, .mkv, .webm]

# Extrae 3 frames por video usando OpenCV
for video in videos:
    - frame0.jpg  # Inicio
    - frame1.jpg  # Medio
    - frame2.jpg  # Final
```

#### Paso 2: Preparación de Imágenes

```python
# Separación clara de assets
static_images = []     # De media/
video_frames = []      # De video_frames/

# Conversión a Base64
for image in all_images:
    - Convertir a RGB
    - Redimensionar (800x800, LANCZOS)
    - Comprimir JPEG (quality=85)
    - Codificar Base64
```

#### Paso 3: Construcción del Prompt

```
ANUNCIO ID: {ad_id}
- IMÁGENES ESTÁTICAS: X
- VIDEO (frames extraídos): Y

📷 IMÁGENES ESTÁTICAS:
[imágenes en Base64]

🎥 FRAMES DE VIDEO:
[frames en Base64]
```

#### Paso 4: Llamada a OpenAI

```python
model: "gpt-4o-mini"
max_tokens: 16000
prompt: prompt_forensic_compact.txt

# Análisis solicitado:
- Visual forensics (composición, colores, elementos)
- Semiotic analysis (significados, símbolos, narrativa)
- Psychological triggers (escasez, prueba social, FOMO)
- Effectiveness scores (1-10 en 5 métricas)
- Optimization roadmap (acciones específicas)
- COMPARATIVE ANALYSIS (OBLIGATORIO)
```

#### Paso 5: Parseo de Respuesta

```python
# Intenta JSON estándar
json.loads(response)

# Si falla, usa json-repair
repair_json(response)  # Librería especializada

# Si todo falla, estructura básica
fallback_structure()
```

#### Paso 6: Generación de Archivos

```
reports/
├── {run_id}_analysis.json     # JSON parseado completo
└── {run_id}_analysis.md       # Markdown con sección comparativa destacada
```

**Estructura del Markdown generado:**

```markdown
# Análisis de Campaña: {run_id}

**Fecha:** 2025-11-18 10:30:45
**Anuncios analizados:** 10
**Imágenes estáticas:** 105
**Frames de video:** 12
**Tokens usados:** 54,328

---

## 🏆 ANÁLISIS COMPARATIVO

### 🥇 GANADOR: {ad_id}

**Razones:** [Análisis detallado]
**Fortalezas clave:**

- Stopping power excepcional
- CTA claro y urgente
- Narrativa visual coherente

### 🥈 SEGUNDO LUGAR: {ad_id}

[Análisis y áreas de mejora]

### 📊 TABLA DE RANKING

| Rank | Anuncio ID | Score | Mejor Atributo  |
| ---- | ---------- | ----- | --------------- |
| 1    | 123456     | 9.2   | stopping_power  |
| 2    | 789012     | 8.7   | message_clarity |
| ...  | ...        | ...   | ...             |

---

## 📄 Respuesta Completa de OpenAI

[Contenido JSON formateado]
```

---

### 4️⃣ **Conversión a PDF (Opcional)**

**Endpoint:** `POST /api/v1/apify/facebook/json-to-pdf`

**Proceso:**

1. Carga JSON del análisis previo
2. Usa OpenAI para formatear en Markdown profesional
3. Convierte Markdown a PDF con ReportLab

**Salida:**

```
reports/
├── {run_id}_formatted.md      # Markdown formateado por IA
└── {run_id}_report.pdf         # PDF final
```

---

## 📦 Estructura JSON del Análisis

```json
{
  "metadata": {
    "report_title": "Análisis de Activos Visuales",
    "total_assets_analyzed": 117,
    "campaign_id": "yJeKF48KH4pPFspOY"
  },
  "executive_summary": {
    "overview": "...",
    "key_findings": "...",
    "strategic_implications": "..."
  },
  "assets_analysis": [
    {
      "asset_id": "829095826733139",
      "file_name": "829095826733139_image.jpg",
      "visual_forensics": "...",
      "semiotic_analysis": "...",
      "psychological_triggers": "...",
      "effectiveness_scores": {
        "stopping_power": "8/10 - ...",
        "message_clarity": "9/10 - ...",
        "emotional_relevance": "7/10 - ...",
        "cta_strength": "9/10 - ...",
        "brand_recall": "8/10 - ..."
      },
      "optimization_roadmap": [
        {
          "action": "Agregar urgencia temporal en CTA",
          "priority": "ALTA",
          "rationale": "...",
          "expected_impact": "+15% CTR"
        }
      ]
    }
  ],
  "comparative_analysis": {
    "methodology": "...",
    "winner": {
      "asset_id": "829095826733139",
      "reasons": "...",
      "key_strengths": ["...", "...", "..."]
    },
    "runner_up": {
      "asset_id": "1321488129781413",
      "reasons": "...",
      "areas_to_improve": ["...", "..."]
    },
    "underperformers": [...],
    "ranking_table": [
      {
        "rank": 1,
        "asset_id": "829095826733139",
        "overall_score": "9.2",
        "best_attribute": "stopping_power"
      }
    ]
  },
  "cross_asset_analysis": {
    "common_strengths": "...",
    "common_weaknesses": "...",
    "pattern_insights": "..."
  },
  "global_conclusions": {
    "summary": "...",
    "priority_recommendations": ["...", "...", "..."]
  },
  "strategic_roadmap": {
    "immediate_actions": "...",
    "short_term": "...",
    "long_term": "..."
  }
}
```

---

## 🛠️ Tecnologías Utilizadas

### Backend Core

- **FastAPI** 0.104.1 - Framework async
- **Uvicorn** 0.24.0 - Servidor ASGI
- **Pydantic** 2.5.0 - Validación de datos

### Procesamiento de Multimedia

- **OpenCV** 4.8.1.78 - Extracción de frames
- **Pillow** 10.1.0 - Procesamiento de imágenes
- **ffmpeg** - Conversión de videos

### IA y Análisis

- **OpenAI API** - GPT-4o-mini (Vision)
- **json-repair** 0.25.3 - Reparación de JSON malformado

### Scraping y Datos

- **Apify Client** - Actors de scraping
- **pandas** 2.1.3 - Manipulación de datos
- **requests** 2.31.0 - HTTP client

### Generación de Reportes

- **ReportLab** 4.0.7 - PDFs
- **python-markdown** - Conversión MD

### Almacenamiento (Opcional)

- **Google Cloud Storage** - Archivos multimedia
- **BigQuery** - Analytics avanzados

---

## ⚙️ Configuración

### Variables de Entorno (`.env`)

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Apify
APIFY_TOKEN=apify_api_...

# Configuración de Análisis
PROMPT_FILE=prompt_forensic_compact.txt

# Google Cloud (Opcional)
GOOGLE_APPLICATION_CREDENTIALS=credentials/credentials.json
GCS_BUCKET_NAME=analizador-anuncios
```

---

## 📂 Estructura de Directorios

```
web_analizador_anuncios/
├── api_service/                    # Backend FastAPI
│   ├── main.py                     # Punto de entrada
│   ├── app/
│   │   ├── api/routes/
│   │   │   └── apify/
│   │   │       └── facebook/
│   │   │           ├── routes/
│   │   │           │   └── analysis.py    # ⭐ Análisis con OpenAI
│   │   │           └── utils/
│   │   │               └── pdf_generator.py
│   │   ├── processors/
│   │   │   ├── datasets/
│   │   │   │   └── saved_datasets/
│   │   │   │       └── facebook/
│   │   │   │           ├── {run_id}/
│   │   │   │           │   ├── media/
│   │   │   │           │   ├── video_frames/
│   │   │   │           │   └── {run_id}.csv
│   │   │   │           └── reports/
│   │   │   │               ├── {run_id}_analysis.json
│   │   │   │               ├── {run_id}_analysis.md
│   │   │   │               └── {run_id}_report.pdf
│   │   │   └── facebook/
│   │   │       └── media_preparation/
│   │   │           └── local_file_downloader.py
│   │   └── services/
│   │       └── apify_service.py
│   ├── prompts/
│   │   ├── prompt_forensic_compact.txt    # ⭐ Prompt principal
│   │   └── prompt_forensic_deep.txt
│   └── credentials/
│       ├── credentials.json
│       └── credsDrive.json
├── frontend/                       # Django frontend
│   ├── manage.py
│   ├── dashboard/
│   └── templates/
├── docs/                          # Documentación
│   ├── ANALYSIS_ENDPOINT.md
│   ├── DATASET_ENDPOINTS.md
│   └── FACEBOOK_API.md
├── requirements.txt               # Dependencias Python
├── .env                          # Variables de entorno
└── README.md
```

---

## 🚀 Casos de Uso

### 1. Análisis de Campaña Competitiva

```bash
# 1. Scrapear anuncios de competidor
POST /api/v1/apify/facebook/scrape
{
  "keywords": "Nike shoes",
  "country": "US",
  "language": "en"
}

# 2. Descargar multimedia
POST /api/v1/apify/facebook/download-media?run_id=abc123

# 3. Analizar y comparar
POST /api/v1/apify/facebook/analyze-and-generate-pdf?run_id=abc123&top_n=20

# 4. Obtener ganador y mejores prácticas
# Resultado: Markdown con ranking y recomendaciones accionables
```

### 2. Optimización de Creativos

```bash
# Analizar tus propios anuncios
POST /api/v1/apify/facebook/analyze-and-generate-pdf?run_id=my_ads&top_n=50

# Resultado incluye:
# - Scores de efectividad (1-10)
# - Optimization roadmap con prioridades
# - Áreas de mejora específicas
```

### 3. Benchmark de Industria

```bash
# Scrapear múltiples keywords
for keyword in ["keyword1", "keyword2", "keyword3"]:
    scrape(keyword)
    download_media()
    analyze()

# Comparar resultados entre datasets
# Identificar tendencias y best practices
```

---

## 📊 Métricas y Análisis

### Scores de Efectividad (1-10)

1. **Stopping Power** - Capacidad de detener el scroll
2. **Message Clarity** - Claridad del mensaje (3 segundos)
3. **Emotional Relevance** - Conexión emocional
4. **CTA Strength** - Fuerza del call-to-action
5. **Brand Recall** - Recordación de marca

### Gatillos Psicológicos Detectados

- Escasez (urgencia temporal)
- Prueba social (testimonios, números)
- Autoridad (expertos, certificaciones)
- Reciprocidad (valor gratuito)
- Pertenencia (identificación tribal)
- Contraste (antes/después)
- FOMO (aversión a la pérdida)

---

## 🔧 Comandos Útiles

### Iniciar Backend

```bash
cd api_service
python main.py
# Server en http://localhost:8001
# Docs en http://localhost:8001/docs
```

### Iniciar Frontend

```bash
cd frontend
python manage.py runserver 8002
# Dashboard en http://localhost:8002
```

### Verificar Entorno

```bash
python verify_env.py
```

---

## 🐛 Troubleshooting

### OpenCV no disponible

```bash
pip install opencv-python==4.8.1.78
```

### JSON malformado de OpenAI

- ✅ Sistema usa `json-repair` automáticamente
- ✅ Fallback a estructura básica si falla
- ✅ Siempre genera reportes, incluso con errores

### Videos no procesados

- ✅ Sistema extrae frames automáticamente
- ✅ Detecta: .mp4, .avi, .mov, .mkv, .webm
- ✅ Extrae 3 frames por video (inicio, medio, fin)

---

## 📈 Roadmap Futuro

- [ ] Soporte para Instagram y TikTok
- [ ] Dashboard interactivo con gráficos
- [ ] A/B testing automatizado
- [ ] Machine Learning para predicción de performance
- [ ] Integración con plataformas de ads (Facebook Ads Manager)
- [ ] Exportación a PowerPoint

---

## 📝 Notas Importantes

1. **Tokens OpenAI:** Análisis de 10 anuncios consume ~50-60k tokens
2. **Costos Apify:** Cada scraping consume créditos según volumen
3. **Límites de Rate:** OpenAI tiene límites de RPM (requests per minute)
4. **Storage:** Videos y frames pueden ocupar espacio significativo

---

## 👥 Contribución

Para agregar nuevas funcionalidades:

1. Crear branch desde `arreglo-scrapper`
2. Implementar cambios
3. Actualizar documentación
4. Pull request con descripción detallada

---

## 📄 Licencia

Proyecto privado - Workana 2025
