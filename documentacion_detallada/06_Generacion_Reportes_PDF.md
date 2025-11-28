# 06. Generación de Reportes PDF

## 📋 Descripción General

El sistema genera reportes PDF profesionales y detallados a partir del análisis JSON de OpenAI. Utiliza ReportLab para crear documentos empresariales listos para presentar a clientes o stakeholders.

## 🎯 Propósito

- Generar reportes profesionales en formato PDF
- Presentar análisis de forma visual y estructurada
- Facilitar distribución y archivo de reportes
- Proporcionar documentos listos para clientes
- Mantener consistencia visual y de marca

## 🔧 Implementación Técnica

### Tecnología Principal

**ReportLab**: Biblioteca Python para generación de PDFs programática

**Ventajas**:
- Generación programática completa
- Control total sobre diseño y layout
- Soporte para gráficos y tablas
- Compatible con múltiples plataformas
- Resultados profesionales de alta calidad

### Módulos y Archivos

- `api_service/app/api/routes/apify/facebook/modules/campaign_analysis/pdf_renderer.py`: Generador principal
- `api_service/app/services/pdf_generator/`: Servicios de generación (si existe)
- `pdf_generator_service_base.py`: Clase base para generación

### Clase Principal

```python
class EnhancedPDFGenerator:
    """Generador de reportes PDF mejorado con gráficos y diseño premium"""
    
    def __init__(self, output_path: str, data: Dict[str, Any]):
        self.output_path = output_path
        self.data = data
        self.styles = getSampleStyleSheet()
        self.brand_color = self._determine_brand_color()
        self._create_custom_styles()
```

## 🎨 Diseño y Estilos

### Paleta de Colores Profesional

```python
THEME_COLORS = {
    'primary': '#1e3a8a',          # Azul oscuro principal
    'primary_light': '#3b82f6',    # Azul claro
    'text_dark': '#1e293b',        # Texto oscuro
    'text_body': '#334155',        # Texto cuerpo
    'text_light': '#64748b',       # Texto claro
    'accent_success': '#059669',   # Verde éxito
    'accent_warning': '#d97706',   # Naranja advertencia
    'accent_danger': '#b91c1c',    # Rojo peligro
    'accent_info': '#0891b2',      # Azul información
    'divider': '#e2e8f0',          # Divisor
    'bg_light': '#f8fafc',         # Fondo claro
}
```

### Estilos Tipográficos

#### Título del Documento

```python
DocTitle: {
    font: 'Helvetica-Bold',
    size: 28pt,
    color: White,
    alignment: Center
}
```

#### Encabezados de Sección

```python
SectionHead: {
    font: 'Helvetica-Bold',
    size: 16pt,
    color: Brand Color,
    spacing: 24pt before, 14pt after
}
```

#### Cuerpo de Texto

```python
DeepBody: {
    font: 'Helvetica',
    size: 10pt,
    leading: 16pt,
    color: Text Body,
    alignment: Justify
}
```

### Configuración de Página

```python
SimpleDocTemplate(
    output_path,
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2*cm,
    bottomMargin=2*cm
)
```

**Dimensiones A4**: 210mm x 297mm (8.27" x 11.69")

## 📄 Estructura del Reporte

### 1. Portada

**Elementos incluidos**:
- Título del reporte
- Fecha de generación
- Tono/marca detectada
- Subtítulo descriptivo

**Diseño**:
- Header con color de marca
- Centrado vertical y horizontal
- Espaciado profesional

### 2. Resumen Ejecutivo

**Contenido**:
- Performance Overview (mínimo 200 palabras)
- Common Success Patterns
- Puntuación Global
- Indicadores Clave (KPIs)

**Elementos visuales**:
- Barras de progreso para scores
- Tablas comparativas
- Gráficos de distribución

### 3. Top 10 Análisis

**Para cada anuncio en el top 10**:

- **Ranking**: Posición (#1, #2, etc.)
- **Métricas**:
  - Primary Metric Value
  - CTR (Click-Through Rate)
  - Spend (Gasto estimado)
- **Forensic Breakdown**:
  - Hook Strategy
  - Audio Mood
  - Narrative Structure
- **Expert Scores** (1-10):
  - Visual Hook
  - Storytelling
  - Brand Integration
  - Conversion Driver
- **Key Takeaway**: Conclusión principal

**Visualización**:
- Tablas estructuradas
- Barras de progreso para scores
- Códigos de color por performance

### 4. Profundización Estratégica

**Secciones**:
- Visual Strategy
- Copywriting Audit
- Audience Resonance
- Psychological Triggers

**Formato**:
- Párrafos justificados
- Listas con bullets
- Citas destacadas
- Ejemplos concretos

### 5. Recomendaciones Estratégicas

**Estructura**:
- Prioridad (ALTA, MEDIA, BAJA)
- Acción específica
- Rationale (por qué)
- Expected Impact

**Visualización**:
- Tarjetas por prioridad
- Códigos de color
- Iconos indicativos

### 6. Conclusiones y Próximos Pasos

**Contenido**:
- Resumen final
- Recomendaciones clave
- Roadmap de implementación
- Próxima revisión sugerida

## 🔄 Proceso de Generación

### Paso 1: Parsear JSON

```python
def parse_analysis_json(analysis_json: Dict[str, Any]) -> Dict[str, Any]:
    """Parsea el campo 'analysis' si está en formato string"""
    if 'analysis' in analysis_json and isinstance(analysis_json['analysis'], str):
        # Remover markdown code blocks si existen
        analysis_str = analysis_json['analysis']
        if '```json' in analysis_str:
            analysis_str = analysis_str.split('```json')[1].split('```')[0]
        
        return json.loads(analysis_str.strip())
    return analysis_json
```

### Paso 2: Mapear Datos

```python
def map_openai_to_pdf_data(openai_json: Dict) -> Dict:
    """Mapea estructura de OpenAI a estructura de PDF"""
    return {
        'report_meta': openai_json.get('report_meta', {}),
        'executive_summary': openai_json.get('executive_summary', {}),
        'top_10_analysis': openai_json.get('top_10_analysis', []),
        'strategic_recommendations': openai_json.get('strategic_recommendations', [])
    }
```

### Paso 3: Crear Documento

```python
doc = SimpleDocTemplate(
    str(output_path),
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2*cm,
    bottomMargin=2*cm,
    title=f"Análisis de Campaña - {run_id}"
)
```

### Paso 4: Construir Contenido

```python
story = []  # Lista de elementos del PDF

# Portada
story.append(create_cover_page(data))

# Resumen ejecutivo
story.append(create_executive_summary(data))

# Top 10
story.append(create_top_10_analysis(data))

# Recomendaciones
story.append(create_recommendations(data))

# Generar PDF
doc.build(story, onFirstPage=add_header, onLaterPages=add_header)
```

### Paso 5: Agregar Headers y Footers

```python
def add_header(canvas, doc):
    """Agrega header con título y fecha"""
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(2*cm, A4[1] - 1.5*cm, "ANÁLISIS DE CAMPAÑA")
    canvas.restoreState()

def add_footer(canvas, doc):
    """Agrega footer con número de página"""
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    page_num = canvas.getPageNumber()
    canvas.drawRightString(A4[0] - 2*cm, 1*cm, f"Página {page_num}")
    canvas.restoreState()
```

## 📊 Elementos Visuales

### Tablas

```python
def create_comparison_table(data_rows, headers):
    """Crea tabla comparativa con estilos"""
    table = Table(data_rows, colWidths=[...])
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), THEME_COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    return table
```

### Barras de Progreso

```python
def create_progress_bar(value, max_value=10, width=3*inch):
    """Crea barra de progreso visual"""
    drawing = Drawing(width, 0.3*inch)
    
    # Fondo
    drawing.add(Rect(0, 0, width, 0.3*inch, 
                    fillColor=THEME_COLORS['bg_light'],
                    strokeColor=THEME_COLORS['divider']))
    
    # Barra de progreso
    progress_width = (value / max_value) * width
    drawing.add(Rect(0, 0, progress_width, 0.3*inch,
                    fillColor=THEME_COLORS['primary']))
    
    return drawing
```

### Gráficos

El sistema puede generar:
- Gráficos de barras para comparaciones
- Gráficos de pastel para distribución
- Visualizaciones de scores

## 📁 Estructura de Archivos

### Ubicación de PDFs Generados

```
datasets/facebook/{run_id}/reports/
└── Reporte_Analisis_Completo_{run_id}.pdf
```

### Nomenclatura

- Formato: `Reporte_Analisis_Completo_{run_id}.pdf`
- Ejemplo: `Reporte_Analisis_Completo_bfMXWLphPQcDmBsrz.pdf`

## 🔗 Integración con Endpoints

### Generación Automática

Los endpoints de análisis generan PDFs automáticamente:

```python
# En analyze-local-and-pdf y analyze-url-with-download
pdf_generator = PDFGenerator(str(pdf_path))
final_pdf_path = pdf_generator.generate(analysis_data)
```

### Descarga de PDF

```http
GET /api/v1/apify/facebook/pdf/{run_id}
```

Retorna el PDF como descarga directa (`application/pdf`).

## ⚙️ Configuración y Personalización

### Cambiar Estilos

Modificar `pdf_renderer.py`:

```python
# Cambiar color de marca
self.brand_color = colors.HexColor('#TU_COLOR_AQUI')

# Cambiar tamaño de fuente
fontSize=12  # Cambiar según necesidad

# Cambiar márgenes
leftMargin=3*cm  # Ajustar según diseño
```

### Agregar Secciones

```python
def create_custom_section(data):
    """Agrega sección personalizada"""
    elements = []
    elements.append(Paragraph("Título", style))
    elements.append(Paragraph("Contenido", body_style))
    return elements

# Agregar al story
story.extend(create_custom_section(data))
```

### Cambiar Formato de Página

```python
# Para formato Letter (US)
from reportlab.lib.pagesizes import letter
doc = SimpleDocTemplate(path, pagesize=letter)

# Para formato personalizado
custom_size = (11*inch, 8.5*inch)  # Width x Height
doc = SimpleDocTemplate(path, pagesize=custom_size)
```

## 📈 Performance

### Tiempos de Generación

| Tamaño del Reporte | Tiempo Aproximado |
|-------------------|-------------------|
| 5-10 páginas | 2-5 segundos |
| 10-20 páginas | 5-10 segundos |
| 20-30 páginas | 10-15 segundos |

### Optimizaciones

1. **Streaming**: Genera mientras procesa
2. **Lazy Loading**: Carga imágenes solo cuando necesario
3. **Caching**: Reutiliza estilos y configuración
4. **Compresión**: PDFs optimizados automáticamente

## 🔍 Troubleshooting

### Problema: PDF no se genera

**Síntomas**:
- Error al generar PDF
- Archivo no creado

**Soluciones**:
1. Verificar que ReportLab esté instalado: `pip install reportlab`
2. Verificar permisos de escritura en directorio
3. Verificar que el JSON sea válido
4. Revisar logs de errores

### Problema: PDF con formato incorrecto

**Síntomas**:
- Texto cortado
- Tablas desalineadas
- Imágenes fuera de lugar

**Soluciones**:
1. Ajustar márgenes del documento
2. Verificar ancho de tablas
3. Ajustar tamaño de imágenes
4. Revisar estilos personalizados

### Problema: PDF muy grande

**Síntomas**:
- Archivo PDF >10MB
- Lento de descargar

**Soluciones**:
1. Comprimir imágenes incluidas
2. Reducir calidad de gráficos
3. Eliminar elementos no esenciales
4. Usar compresión PDF

## 📝 Mejores Prácticas

### Diseño

1. **Consistencia**: Usar mismos estilos en todo el documento
2. **Legibilidad**: Tamaños de fuente apropiados (mínimo 10pt)
3. **Espaciado**: Espacio adecuado entre secciones
4. **Colores**: Usar colores de manera consistente

### Contenido

1. **Estructura clara**: Organizar información lógicamente
2. **Resúmenes**: Incluir resúmenes ejecutivos
3. **Visualizaciones**: Usar gráficos para datos complejos
4. **Accionabilidad**: Recomendaciones claras y específicas

### Técnico

1. **Validación**: Validar JSON antes de generar
2. **Manejo de errores**: Capturar y manejar errores graciosamente
3. **Logging**: Registrar proceso de generación
4. **Testing**: Probar con diferentes estructuras de datos

---

**Última actualización**: Noviembre 2025

