# 07. Frontend Prototipo

## 📋 Descripción General

El sistema incluye un prototipo de frontend web simple pero funcional que permite a los usuarios interactuar con el sistema de análisis mediante una interfaz visual. Está construido con HTML, CSS y JavaScript vanilla (sin frameworks).

## 🎯 Propósito

- Proporcionar interfaz visual para análisis
- Facilitar uso para usuarios no técnicos
- Demostrar capacidades del sistema
- Permitir pruebas rápidas de funcionalidades
- Servir como base para frontend más complejo

## 🏗️ Arquitectura

### Stack Tecnológico

- **HTML5**: Estructura semántica
- **CSS3**: Estilos modernos con variables CSS
- **JavaScript (ES6+)**: Lógica interactiva sin frameworks
- **Lucide Icons**: Iconos modernos y ligeros
- **Google Fonts (Outfit)**: Tipografía profesional

### Estructura de Archivos

```
frontend/prototype/
├── index.html      # Página principal
├── styles.css      # Estilos completos
└── script.js       # Lógica JavaScript
```

### Servidor Simple

El frontend se sirve mediante un servidor HTTP simple de Python:

```
frontend_server.py  # Servidor HTTP en puerto 3001
```

## 📄 Estructura HTML

### Elementos Principales

#### Header

```html
<header>
    <h1>Analizador de Anuncios</h1>
    <p>Optimiza tus creativos con Inteligencia Artificial</p>
</header>
```

#### Formulario Principal

```html
<form id="analysisForm">
    <!-- Selector de Modo -->
    <div class="mode-selector">
        <button type="button" class="mode-btn active" data-mode="url">
            Analizar URL
        </button>
        <button type="button" class="mode-btn" data-mode="runid">
            Analizar Run ID
        </button>
    </div>
    
    <!-- Inputs dinámicos según modo -->
    <!-- Botón de envío -->
</form>
```

#### Sección de Resultados

```html
<div id="resultsSection" class="hidden">
    <h2>Resultados del Análisis</h2>
    <p id="resultsMessage"></p>
    <a id="pdfLink" href="#">Descargar PDF</a>
    <a id="jsonLink" href="#">Ver JSON</a>
</div>
```

## 🎨 Estilos CSS

### Variables CSS

```css
:root {
    --primary-color: #3b82f6;
    --secondary-color: #1e40af;
    --success-color: #10b981;
    --danger-color: #ef4444;
    --bg-color: #f8fafc;
    --text-color: #1e293b;
    --border-radius: 12px;
    --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
```

### Componentes Principales

#### Cards

```css
.card {
    background: white;
    border-radius: var(--border-radius);
    padding: 2rem;
    box-shadow: var(--shadow);
}
```

#### Botones

```css
.btn-primary {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: white;
    border: none;
    padding: 1rem 2rem;
    border-radius: var(--border-radius);
    cursor: pointer;
    transition: transform 0.2s;
}

.btn-primary:hover {
    transform: translateY(-2px);
}
```

#### Inputs

```css
.input-wrapper textarea,
.input-wrapper input {
    width: 100%;
    padding: 0.75rem;
    border: 2px solid #e2e8f0;
    border-radius: var(--border-radius);
    font-size: 1rem;
    transition: border-color 0.3s;
}

.input-wrapper textarea:focus,
.input-wrapper input:focus {
    outline: none;
    border-color: var(--primary-color);
}
```

## ⚙️ Funcionalidad JavaScript

### Configuración Inicial

```javascript
const API_BASE = 'http://localhost:8001';
let currentMode = 'url';  // 'url' o 'runid'
```

### Selector de Modo

```javascript
modeBtns.forEach((btn) => {
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        
        // Actualizar estado activo
        modeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Cambiar modo
        currentMode = btn.dataset.mode;
        
        // Mostrar/ocultar inputs según modo
        if (currentMode === 'url') {
            urlGroup.classList.remove('hidden');
            runIdGroup.classList.add('hidden');
        } else {
            urlGroup.classList.add('hidden');
            runIdGroup.classList.remove('hidden');
        }
    });
});
```

### Envío de Formulario

```javascript
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Validar input según modo
    let inputValue;
    if (currentMode === 'url') {
        inputValue = adUrlInput.value.trim();
        if (!inputValue) {
            shakeElement(adUrlInput);
            return;
        }
    } else {
        inputValue = runIdInput.value.trim();
        if (!inputValue) {
            shakeElement(runIdInput);
            return;
        }
    }
    
    // Estado de carga
    submitBtn.disabled = true;
    btnText.textContent = 'Analizando...';
    
    try {
        let response;
        
        if (currentMode === 'url') {
            response = await fetch(`${API_BASE}/api/v1/apify/facebook/analyze-url-with-download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: inputValue,
                    count: 100,
                    timeout: 600
                })
            });
        } else {
            response = await fetch(`${API_BASE}/api/v1/apify/facebook/analyze-local-and-pdf?run_id=${encodeURIComponent(inputValue)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error en el análisis');
        }
        
        const data = await response.json();
        
        // Mostrar resultados
        displayResults(data);
        
        // Descargar PDF automáticamente
        if (data.pdf_path && data.run_id) {
            await downloadPDF(data.run_id);
        }
        
    } catch (error) {
        console.error('Error:', error);
        alert(`Error: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        btnText.textContent = 'Analizar';
    }
});
```

### Descarga Automática de PDF

```javascript
async function downloadPDF(runId) {
    try {
        const pdfUrl = `${API_BASE}/api/v1/apify/facebook/pdf/${runId}`;
        const response = await fetch(pdfUrl);
        
        if (!response.ok) {
            console.error('Error descargando PDF:', response.statusText);
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Reporte_Analisis_Completo_${runId}.pdf`;
        document.body.appendChild(a);
        a.click();
        
        // Limpiar
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
    } catch (error) {
        console.error('Error al descargar PDF:', error);
    }
}
```

### Visualización de Resultados

```javascript
function displayResults(data) {
    const runId = data.run_id || 'N/A';
    
    // Mensaje de éxito
    resultsMessage.textContent = `Análisis completado exitosamente para Run ID: ${runId}`;
    
    // Link a PDF
    if (data.pdf_path && runId) {
        pdfLink.href = `${API_BASE}/api/v1/apify/facebook/pdf/${runId}`;
        pdfLink.style.display = 'flex';
    }
    
    // Link a JSON
    if (data.json_report) {
        const jsonFilename = data.json_report.split('\\').pop().split('/').pop();
        jsonLink.href = `${API_BASE}/api/v1/apify/facebook/saved/${runId}/reports/${jsonFilename}`;
        jsonLink.style.display = 'flex';
    }
    
    // Mostrar sección
    resultsSection.classList.remove('hidden');
    
    // Scroll suave a resultados
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
```

## 🎯 Modos de Operación

### Modo URL

**Funcionalidad**:
- Analiza desde URL de Facebook Ads Library
- Realiza scraping completo
- Genera análisis y PDF

**Endpoint utilizado**:
```
POST /api/v1/apify/facebook/analyze-url-with-download
```

**Input requerido**:
- URL completa de Facebook Ads Library

### Modo Run ID

**Funcionalidad**:
- Analiza dataset ya descargado
- Usa datos locales existentes
- Genera análisis y PDF más rápido

**Endpoint utilizado**:
```
POST /api/v1/apify/facebook/analyze-local-and-pdf?run_id={run_id}
```

**Input requerido**:
- Run ID de dataset existente

## 🎨 Características de UI/UX

### Animaciones

#### Shake Animation (Validación)

```css
@keyframes shake {
    10%, 90% { transform: translate3d(-1px, 0, 0); }
    20%, 80% { transform: translate3d(2px, 0, 0); }
    30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
    40%, 60% { transform: translate3d(4px, 0, 0); }
}
```

#### Transiciones

```css
.card {
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}
```

### Estados Visuales

#### Loading State

```javascript
submitBtn.disabled = true;
btnText.textContent = 'Analizando...';
submitBtn.style.opacity = '0.8';
```

#### Success State

```javascript
btnText.textContent = '¡Análisis Completado!';
submitBtn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
```

#### Error State

```javascript
btnText.textContent = 'Error en el análisis';
submitBtn.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
```

## 🔧 Personalización

### Cambiar Puerto de API

```javascript
// En script.js, línea ~26
const API_BASE = 'http://localhost:8001';  // Cambiar según necesidad
```

### Modificar Estilos

Editar `styles.css`:
- Cambiar colores en variables CSS
- Modificar espaciado y tamaños
- Ajustar responsive design
- Personalizar animaciones

### Agregar Nuevos Campos

1. Agregar HTML en `index.html`
2. Agregar lógica en `script.js`
3. Incluir en body de fetch request
4. Agregar estilos si necesario

### Agregar Nuevos Modos

```javascript
// Agregar botón en HTML
<button type="button" class="mode-btn" data-mode="nuevomodo">
    Nuevo Modo
</button>

// Agregar lógica en JavaScript
if (currentMode === 'nuevomodo') {
    // Lógica específica
    response = await fetch(`${API_BASE}/nuevo-endpoint`, {...});
}
```

## 🚀 Ejecución

### Iniciar Servidor Frontend

```bash
python frontend_server.py
```

O usar el script principal:

```bash
python start.py  # Inicia API + Frontend
```

### Acceder al Frontend

```
http://localhost:3001
```

## 🔍 Troubleshooting

### Problema: CORS Error

**Síntoma**: Error en consola sobre CORS

**Solución**: Verificar que API permita origen `http://localhost:3001`

```python
# En api_service/main.py
CORSMiddleware(
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"]
)
```

### Problema: Iconos no aparecen

**Síntoma**: Iconos no se muestran

**Solución**: Verificar que Lucide esté cargado

```javascript
// Al final del script
if (typeof lucide !== 'undefined' && lucide.createIcons) {
    lucide.createIcons();
}
```

### Problema: PDF no se descarga

**Síntoma**: Error al descargar PDF

**Soluciones**:
1. Verificar que el endpoint de PDF funcione
2. Verificar permisos del navegador para descargas
3. Revisar consola para errores específicos

## 📱 Responsive Design

### Breakpoints

```css
@media (max-width: 768px) {
    .content-grid {
        grid-template-columns: 1fr;
    }
    
    .card {
        padding: 1rem;
    }
}
```

### Adaptaciones Móviles

- Grid de una columna en móviles
- Botones de tamaño táctil
- Textos legibles en pantallas pequeñas
- Formularios optimizados

## 🎯 Próximas Mejoras Potenciales

1. **Progreso en tiempo real**: Mostrar progreso del análisis
2. **Historial**: Guardar análisis previos
3. **Preview de PDF**: Mostrar preview antes de descargar
4. **Comparación**: Comparar múltiples análisis
5. **Filtros avanzados**: Más opciones de filtrado

---

**Última actualización**: Noviembre 2025

