# 08. Configuración de Prompts

## 📋 Descripción General

El sistema implementa un sistema flexible de prompts que permite personalizar completamente cómo la IA analiza los anuncios. Los prompts pueden configurarse mediante variables de entorno, archivos externos o usando los valores por defecto del sistema.

## 🎯 Propósito

- Permitir personalización completa del análisis
- Facilitar experimentación con diferentes enfoques
- Mantener prompts profesionales por defecto
- Permitir versionado de prompts
- Facilitar colaboración entre equipos

## 🔧 Sistema de Carga de Prompts

### Jerarquía de Prioridad

El sistema busca prompts en el siguiente orden:

1. **Variable de entorno `PROMPT`** (Prioridad 1 - Máxima)
2. **Archivo definido en `PROMPT_FILE`** (Prioridad 2)
3. **`DEFAULT_PROMPT` del módulo** (Prioridad 3)
4. **Prompt básico de emergencia** (Prioridad 4 - Mínima)

### Implementación

```python
# Cargar prompt desde .env o archivo
prompt_template = os.getenv('PROMPT')

if not prompt_template:
    prompt_file_name = os.getenv('PROMPT_FILE', 'prompt.txt')
    api_service_dir = Path(__file__).parent.parent.parent.parent.parent.parent.parent
    prompt_path = api_service_dir / prompt_file_name
    
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read().strip()
    else:
        try:
            from app.api.routes.apify.facebook.analysis.prompts import DEFAULT_PROMPT
            prompt_template = DEFAULT_PROMPT
        except ImportError:
            prompt_template = "Analiza estos anuncios de Facebook de manera PROFUNDA y DETALLADA. TODO en ESPAÑOL."
```

## 📝 Métodos de Configuración

### Método 1: Variable de Entorno

**Ventajas**:
- Cambio rápido sin modificar archivos
- Ideal para pruebas
- Fácil de sobrescribir

**Configuración**:

```bash
# En .env o exportar directamente
export PROMPT="Tu prompt personalizado aquí"
```

**Ejemplo**:

```bash
export PROMPT="Eres un experto en marketing digital. Analiza estos anuncios enfocándote especialmente en el uso de colores y la psicología del consumidor."
```

### Método 2: Archivo de Prompt

**Ventajas**:
- Prompts complejos y extensos
- Fácil de versionar (Git)
- Compartible entre equipos
- Mejor organización

**Configuración**:

```bash
# Especificar archivo en .env
export PROMPT_FILE="mi_prompt_personalizado.txt"
```

**Ubicación del archivo**:
- Por defecto busca en la raíz del proyecto
- O en la ruta especificada

**Estructura del archivo**:

```
mi_prompt_personalizado.txt
```

### Método 3: Prompt por Defecto del Módulo

**Ubicación**:
```
api_service/app/api/routes/apify/facebook/analysis/prompts.py
```

**Contenido**:

```python
DEFAULT_PROMPT = """
Eres un EXPERTO EN MARKETING DIGITAL con 15+ años de experiencia 
analizando campañas publicitarias para Fortune 500.

Tu misión: Identificar qué anuncio tiene mayor potencial de conversión 
y POR QUÉ.

EVALÚA CADA ANUNCIO EN:

1. COMPOSICIÓN VISUAL (score 0-10)
   - Paleta de colores y contraste
   - Balance y espaciado
   - Jerarquía visual clara
   - Calidad de producción

2. MENSAJE Y COPYWRITING (score 0-10)
   - Claridad de la propuesta de valor
   - Fuerza del CTA (call-to-action)
   - Beneficios vs características
   - Urgencia y escasez

[... más contenido ...]
"""
```

## 🎯 Estructura Recomendada de Prompts

### Componentes Esenciales

#### 1. Definición del Rol

```
Eres un EXPERTO EN [ÁREA] con [X] años de experiencia
analizando [TIPO DE CONTENIDO] para [CONTEXTO].
```

**Ejemplo**:
```
Eres un EXPERTO EN MARKETING DIGITAL con 15+ años de experiencia
analizando campañas publicitarias para Fortune 500.
```

#### 2. Objetivo Claro

```
Tu misión: [OBJETIVO ESPECÍFICO Y ACCIONABLE]
```

**Ejemplo**:
```
Tu misión: Identificar qué anuncio tiene mayor potencial de conversión 
y POR QUÉ.
```

#### 3. Criterios de Evaluación

```
EVALÚA CADA ANUNCIO EN:

1. [CRITERIO 1] (score 0-10)
   - [Subcriterio 1]
   - [Subcriterio 2]
   
2. [CRITERIO 2] (score 0-10)
   - [Subcriterio 1]
   - [Subcriterio 2]
```

#### 4. Formato de Salida

```
RESPONDE SOLO EN FORMATO JSON ESTRICTO con:
- [Campo requerido 1]
- [Campo requerido 2]
- [Campo requerido 3]
```

#### 5. Instrucciones Específicas

```
IMPORTANTE:
- [Instrucción crítica 1]
- [Instrucción crítica 2]
- [Instrucción crítica 3]
```

### Prompt Completo de Ejemplo

```
Eres un experto analista de marketing digital y publicidad. 
IMPORTANTE: Toda tu respuesta debe ser en ESPAÑOL.

Debes analizar anuncios publicitarios de manera profesional 
y proporcionar análisis profundos y detallados.

INSTRUCCIONES CRÍTICAS:
- Retorna ÚNICAMENTE un objeto JSON válido
- No agregues texto adicional antes o después del JSON
- Analiza TODOS los anuncios proporcionados
- Contrasta imágenes estáticas con frames de video
- Proporciona insights profundos basados en análisis visual

FORMATO DE SALIDA REQUERIDO (JSON):
{
  "report_meta": {
    "generated_role": "Senior Data Scientist & Marketing Director",
    "brand_detected": "(Nombre de la marca)",
    "ranking_metric_used": "(Métrica principal)",
    "sample_size": "(Cantidad de anuncios)"
  },
  "executive_summary": {
    "performance_overview": "(Resumen extensivo de 200+ palabras)",
    "common_success_patterns": "(Patrones identificados)"
  },
  "top_10_analysis": [
    {
      "rank": 1,
      "ad_id": "(ID del anuncio)",
      "metrics": {...},
      "forensic_breakdown": {...},
      "expert_scores": {...},
      "key_takeaway": "(Conclusión principal)"
    }
  ],
  "strategic_recommendations": [
    "(Recomendación detallada y accionable)"
  ]
}

CRITERIOS DE EVALUACIÓN:
1. Visual Hook (1-10): Poder de detención visual
2. Storytelling (1-10): Calidad narrativa
3. Brand Integration (1-10): Integración de marca
4. Conversion Driver (1-10): Potencial de conversión

SÉ CRÍTICO pero CONSTRUCTIVO. Usa métricas y evidencia visual.
```

## 📂 Archivos de Prompt Disponibles

El proyecto incluye varios prompts de ejemplo:

```
api_service/prompts/
├── prompt.txt                    # Prompt principal
├── prompt_simple.txt             # Versión simplificada
├── prompt_analysis.txt           # Enfoque en análisis
├── prompt_comparer.txt           # Enfoque comparativo
├── prompt_forensic_compact.txt   # Análisis forense compacto
└── prompt_forensic_deep.txt      # Análisis forense profundo
```

### Características de Cada Prompt

#### `prompt.txt`
- Prompt principal y más completo
- Balance entre detalle y longitud
- Ideal para uso general

#### `prompt_simple.txt`
- Versión simplificada
- Menos detalle pero más rápido
- Ideal para pruebas rápidas

#### `prompt_forensic_compact.txt`
- Análisis forense estructurado
- Formato compacto
- Ideal para análisis técnico

#### `prompt_forensic_deep.txt`
- Análisis forense profundo
- Máximo detalle
- Ideal para análisis exhaustivos

## 🔄 Combinación con Información del Dataset

El sistema combina automáticamente el prompt con información del dataset:

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

content_blocks.append({
    "type": "text",
    "text": dataset_info + "\n\n" + prompt_template
})
```

**Ventajas**:
- La IA conoce el contexto completo
- Ajusta análisis según cantidad de datos
- Entiende el balance de media procesada
- Genera respuestas más precisas

## 🎨 Personalización Avanzada

### Prompts Especializados por Industria

#### E-commerce

```
Enfócate especialmente en:
- Uso de ofertas y descuentos
- Prueba social (testimonios, reviews)
- Urgencia (oferta limitada, stock limitado)
- Calidad de fotos de producto
```

#### SaaS/B2B

```
Enfócate especialmente en:
- Claridad de propuesta de valor
- Demostración de beneficios
- Casos de uso y aplicaciones
- Trust signals (certificaciones, logos de clientes)
```

#### Lifestyle/Marca

```
Enfócate especialmente en:
- Identidad visual de marca
- Storytelling emocional
- Aspiracional (estilo de vida)
- Coherencia de mensaje
```

### Prompts por Objetivo

#### Optimización de CTR

```
Analiza específicamente:
- Elementos que aumentan click-through rate
- Colores y diseño de CTAs
- Mensajes que generan acción inmediata
```

#### Análisis Competitivo

```
Compara estos anuncios con:
- Mejores prácticas de la industria
- Estándares del sector
- Innovaciones y diferenciadores
```

#### Análisis Psicológico

```
Enfócate en:
- Gatillos psicológicos utilizados
- Efectos emocionales
- Técnicas de persuasión
- Respuesta esperada del consumidor
```

## ⚙️ Configuración en Producción

### Variables de Entorno Recomendadas

```env
# Para desarrollo
PROMPT_FILE=prompt_dev.txt

# Para producción
PROMPT_FILE=prompt_prod.txt

# Para pruebas
PROMPT="Prompt corto para pruebas rápidas"
```

### Versionado de Prompts

```
prompts/
├── v1/
│   ├── prompt_v1.txt
│   └── prompt_v1_notes.md
├── v2/
│   ├── prompt_v2.txt
│   └── prompt_v2_notes.md
└── current -> v2/
```

**Ventajas**:
- Historial de cambios
- Rollback fácil
- Comparación entre versiones
- Documentación de mejoras

## 🔍 Testing de Prompts

### Proceso de Testing

1. **Crear prompt de prueba**: Versión corta y específica
2. **Ejecutar análisis**: Con dataset pequeño
3. **Evaluar resultados**: Revisar calidad y estructura
4. **Iterar**: Ajustar según resultados
5. **Validar**: Probar con diferentes datasets

### Métricas de Calidad

- **Completitud**: ¿Incluye todos los campos requeridos?
- **Profundidad**: ¿El análisis es suficientemente detallado?
- **Accionabilidad**: ¿Las recomendaciones son específicas?
- **Consistencia**: ¿El formato es consistente entre análisis?

## ⚠️ Errores Comunes

### Prompt muy largo

**Problema**: Prompt excede límites de tokens

**Solución**: Reducir longitud, mantener solo elementos esenciales

### Prompt muy vago

**Problema**: Respuestas genéricas y poco útiles

**Solución**: Ser más específico en instrucciones y criterios

### Formato JSON incorrecto

**Problema**: Respuestas no siguen formato esperado

**Solución**: Incluir ejemplo claro de estructura JSON en prompt

### Idioma inconsistente

**Problema**: Respuestas en inglés cuando se requiere español

**Solución**: Enfatizar idioma en múltiples lugares del prompt

## 💡 Mejores Prácticas

1. **Ser específico**: Instrucciones claras y concretas
2. **Incluir ejemplos**: Ejemplos de formato esperado
3. **Enfatizar crítico**: Repetir instrucciones importantes
4. **Testear iterativamente**: Probar y ajustar constantemente
5. **Documentar cambios**: Mantener notas de mejoras
6. **Versionar**: Usar control de versiones para prompts

---

**Última actualización**: Noviembre 2025

