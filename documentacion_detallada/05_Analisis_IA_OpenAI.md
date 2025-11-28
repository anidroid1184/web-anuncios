# 05. Análisis con IA usando OpenAI GPT-4o

## 📋 Descripción General

El sistema integra OpenAI GPT-4o con capacidades de visión para analizar anuncios publicitarios de manera profunda y profesional. Combina análisis visual de imágenes y frames de video con procesamiento de texto para generar insights estratégicos.

## 🎯 Propósito

- Analizar elementos visuales de anuncios (composición, colores, diseño)
- Identificar gatillos psicológicos (escasez, prueba social, autoridad)
- Evaluar efectividad de CTAs y mensajes
- Comparar anuncios y determinar rankings
- Generar recomendaciones estratégicas accionables

## 🤖 Modelo Utilizado

### GPT-4o (GPT-4 Optimized)

**Características**:
- **Visión**: Puede analizar imágenes y frames de video
- **Multimodal**: Combina texto e imágenes en un solo análisis
- **Alta resolución**: `detail: "high"` permite análisis detallado
- **JSON estructurado**: Retorna respuestas en formato JSON válido
- **Sin límite de tokens**: Respuestas completas sin truncamiento

### Ventajas sobre otros modelos

- **vs GPT-4**: Mejor calidad de visión, más rápido
- **vs GPT-3.5**: Mucho mejor análisis visual, más preciso
- **vs Claude**: Mejor soporte para JSON estructurado
- **vs Gemini**: Mejor integración con FastAPI, más estable

## 🔧 Implementación Técnica

### Cliente OpenAI

```python
from openai import AsyncOpenAI

api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
openai_client = AsyncOpenAI(api_key=api_key)
```

**AsyncOpenAI**: Cliente asíncrono para mejor performance en FastAPI.

### Configuración de API

```python
response = await openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    response_format={"type": "json_object"}
)
```

**Parámetros clave**:
- `model="gpt-4o"`: Modelo con visión
- `response_format={"type": "json_object"}`: Fuerza respuesta JSON
- Sin `max_tokens`: Permite respuestas completas

## 📤 Construcción del Payload

### Estructura del Mensaje

```python
messages = [
    {
        "role": "system",
        "content": "Eres un experto analista de marketing digital..."
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Información del dataset + Prompt personalizado"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64,...",
                    "detail": "high"
                }
            },
            # ... más imágenes y frames
        ]
    }
]
```

### Componentes del Payload

#### 1. Mensaje del Sistema

Define el rol y contexto del analista:

```
"Eres un experto analista de marketing digital y publicidad. 
IMPORTANTE: Toda tu respuesta debe ser en ESPAÑOL. 
Debes analizar anuncios publicitarios de manera profesional 
y proporcionar análisis profundos y detallados. 
Retorna ÚNICAMENTE un objeto JSON válido sin texto adicional."
```

**Propósito**:
- Establece expertise del modelo
- Define idioma de respuesta
- Instruye formato de salida
- Establece tono profesional

#### 2. Información del Dataset

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

**Proporciona contexto**:
- Cantidad de anuncios a analizar
- Balance de media procesada
- Instrucciones específicas
- Formato esperado

#### 3. Prompt Personalizado

El prompt puede venir de:
1. Variable de entorno `PROMPT`
2. Archivo definido en `PROMPT_FILE`
3. `DEFAULT_PROMPT` del módulo
4. Prompt básico de emergencia

Ver documentación: `08_Configuracion_Prompts.md`

#### 4. Imágenes y Frames

Cada imagen/frame se incluye como:

```python
{
    "type": "image_url",
    "image_url": {
        "url": "data:image/jpeg;base64,{b64}",
        "detail": "high"
    }
}
```

**`detail: "high"`**:
- Permite análisis detallado
- Mejor reconocimiento de texto en imágenes
- Mayor precisión en análisis visual
- Usa más tokens pero vale la pena

### Orden de Contenido

El orden importa para el análisis:

1. **Texto informativo** (dataset info + prompt)
2. **Frames de video** (40% del total)
3. **Imágenes estáticas** (60% del total)

**Razón**: La IA procesa secuencialmente, contexto temprano afecta análisis posterior.

## 📊 Estructura de Respuesta JSON

### Formato Esperado

```json
{
  "report_meta": {
    "generated_role": "Senior Data Scientist & Marketing Director",
    "brand_detected": "Nike",
    "ranking_metric_used": "Engagement Rate",
    "sample_size": "147 anuncios analizados"
  },
  "executive_summary": {
    "performance_overview": "Análisis extensivo de 200+ palabras...",
    "common_success_patterns": "Patrones identificados..."
  },
  "top_10_analysis": [
    {
      "rank": 1,
      "ad_id": "ad_123",
      "metrics": {...},
      "forensic_breakdown": {...},
      "expert_scores": {...},
      "key_takeaway": "..."
    }
  ],
  "strategic_recommendations": [...]
}
```

### Campos Detallados

#### `report_meta`
- Metadata del análisis
- Rol del analista generado
- Marca detectada
- Métrica principal usada

#### `executive_summary`
- **`performance_overview`**: Resumen extensivo (mínimo 200 palabras)
- **`common_success_patterns`**: Patrones visuales/narrativos recurrentes

#### `top_10_analysis`
Array de análisis detallados de los mejores anuncios:

- **`rank`**: Posición en ranking
- **`ad_id`**: Identificador del anuncio
- **`metrics`**: Métricas cuantitativas (CTR, spend, etc.)
- **`forensic_breakdown`**: Análisis forense detallado
  - `hook_strategy`: Gancho visual en primeros 3 segundos
  - `audio_mood`: Descripción del audio (para videos)
  - `narrative_structure`: Estructura narrativa
- **`expert_scores`**: Puntuaciones de 1-10
  - `visual_hook`: Poder de detención visual
  - `storytelling`: Calidad narrativa
  - `brand_integration`: Integración de marca
  - `conversion_driver`: Potencial de conversión
- **`key_takeaway`**: Conclusión principal del anuncio

#### `strategic_recommendations`
Array de recomendaciones detalladas y accionables.

## 🔄 Procesamiento de Respuesta

### Validación Inicial

```python
analysis = response.choices[0].message.content

# Verificar que no esté vacía
if not analysis or len(analysis.strip()) == 0:
    raise HTTPException(500, "OpenAI devolvió respuesta vacía")

# Verificar rechazo
if "no puedo ayudar" in analysis.lower() or "sorry" in analysis.lower():
    raise HTTPException(500, "OpenAI rechazó la solicitud")
```

### Parsing de JSON

```python
try:
    analysis_data = json.loads(analysis)
except json.JSONDecodeError as e:
    # Intentar reparar JSON
    from json_repair import loads as repair_loads
    repaired = repair_loads(analysis)
    analysis_data = repaired if isinstance(repaired, dict) else json.loads(repaired)
```

### Validación de Estructura

```python
# Verificar campos requeridos
required_fields = ["report_meta", "executive_summary", "top_10_analysis"]
for field in required_fields:
    if field not in analysis_data:
        raise ValueError(f"Campo requerido faltante: {field}")

# Validar que sea dict
if not isinstance(analysis_data, dict):
    raise ValueError("Response no es un objeto JSON válido")
```

## 📈 Métricas y Costos

### Tokens Utilizados

```python
tokens_used = response.usage.total_tokens
```

**Componentes**:
- **Input tokens**: Prompt + imágenes (cada imagen usa ~85 tokens base + tokens por resolución)
- **Output tokens**: Respuesta JSON generada

### Estimación de Costos

| Componente | Tokens Estimados | Costo (GPT-4o) |
|------------|------------------|----------------|
| Prompt base | 500-1000 | ~$0.002-0.004 |
| 50 imágenes (high detail) | ~170,000 | ~$0.17 |
| Respuesta JSON | 2000-4000 | ~$0.008-0.016 |
| **Total** | **~173,000** | **~$0.18-0.19** |

**Factores que afectan costo**:
- Cantidad de imágenes/frames
- Tamaño de imágenes (resolución)
- Longitud del prompt
- Complejidad de la respuesta

### Optimización de Costos

1. **Reducir cantidad de assets**: 30 en lugar de 50
2. **Optimizar tamaño de imágenes**: Redimensionar a 600px en lugar de 800px
3. **Simplificar prompt**: Menos instrucciones = menos tokens
4. **Usar `detail: "low"`**: Más barato pero menos preciso (no recomendado)

## ⚠️ Manejo de Errores

### Errores Comunes

#### 1. Respuesta Vacía

```python
if not analysis or len(analysis.strip()) == 0:
    # Guardar para debugging
    save_response_for_debugging(analysis, run_id)
    raise HTTPException(500, "Respuesta vacía de OpenAI")
```

**Causas posibles**:
- Filtros de contenido de OpenAI
- Prompt viola políticas
- Error interno de OpenAI

#### 2. Rechazo por Contenido

```python
rejection_phrases = ["no puedo ayudar", "sorry", "cannot", "i can't"]
if any(phrase in analysis.lower() for phrase in rejection_phrases):
    # Guardar respuesta rechazada
    save_rejected_response(analysis, run_id)
    raise HTTPException(500, "OpenAI rechazó la solicitud")
```

**Causas posibles**:
- Contenido de anuncios viola políticas
- Prompt solicita algo inapropiado
- Detección de contenido sensible

#### 3. JSON Inválido

```python
try:
    data = json.loads(analysis)
except json.JSONDecodeError:
    # Intentar reparar
    repaired = json_repair.loads(analysis)
    data = repaired
```

**Causas posibles**:
- OpenAI agregó texto antes/después del JSON
- JSON mal formado
- Caracteres especiales sin escapar

**Solución**: `json_repair` corrige la mayoría de errores.

#### 4. Estructura Incorrecta

```python
if not isinstance(data, dict):
    raise ValueError("Response no es objeto JSON")
    
if "top_10_analysis" not in data:
    raise ValueError("Campo top_10_analysis faltante")
```

**Solución**: Validación estricta y mensajes de error claros.

### Logging y Debugging

```python
logger.info(f"Respuesta recibida: {len(analysis)} caracteres")
logger.info(f"Tokens usados: {tokens_used}")

# Guardar respuesta cruda para debugging
raw_path = reports_dir / f"{run_id}_raw_response.txt"
with open(raw_path, 'w', encoding='utf-8') as f:
    f.write(analysis)
```

## 🎯 Análisis Específicos Realizados

### Análisis Visual

- **Composición**: Balance, jerarquía, espaciado
- **Colores**: Paleta, contraste, psicología del color
- **Tipografía**: Legibilidad, jerarquía, estilo
- **Elementos visuales**: Iconos, gráficos, fotos

### Análisis Narrativo

- **Hook visual**: Primeros 3 segundos de impacto
- **Storytelling**: Estructura narrativa (problema/solución, UGC, etc.)
- **Mensaje**: Claridad, propuesta de valor
- **CTA**: Efectividad, urgencia, claridad

### Análisis Psicológico

- **Gatillos emocionales**: Escasez, prueba social, autoridad
- **Trust signals**: Testimonios, certificaciones, garantías
- **Urgencia**: Ofertas limitadas, tiempo limitado
- **Relevancia**: Alineación con audiencia objetivo

### Comparación Competitiva

- **Ranking**: Ordenamiento de mejor a peor
- **Diferenciadores**: Qué hace único a cada anuncio
- **Patrones comunes**: Tendencias identificadas
- **Oportunidades**: Gaps y áreas de mejora

## 🔍 Troubleshooting

### Problema: OpenAI rechaza solicitud

**Síntomas**:
- Error 500 con mensaje de rechazo
- Respuesta contiene "no puedo ayudar" o similar

**Soluciones**:
1. Revisar prompt (puede violar políticas)
2. Verificar contenido de anuncios
3. Revisar respuesta guardada para debugging
4. Modificar prompt para ser más específico

### Problema: JSON inválido

**Síntomas**:
- Error de parsing JSON
- `json.JSONDecodeError`

**Soluciones**:
1. `json_repair` corrige automáticamente
2. Verificar respuesta guardada
3. Revisar prompt para ser más explícito sobre formato JSON
4. Usar `response_format={"type": "json_object"}`

### Problema: Análisis superficial

**Síntomas**:
- Respuestas muy cortas
- Falta de detalle en análisis

**Soluciones**:
1. Mejorar prompt con instrucciones más específicas
2. Aumentar cantidad de imágenes analizadas
3. Usar `detail: "high"` en imágenes
4. Agregar ejemplos en el prompt

---

**Última actualización**: Noviembre 2025

