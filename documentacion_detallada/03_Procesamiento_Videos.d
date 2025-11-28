# 03. Procesamiento de Videos y Extracción de Frames

## 📋 Descripción General

El sistema incluye capacidades avanzadas para procesar videos de anuncios, detectarlos automáticamente y extraer frames estratégicamente distribuidos para análisis con IA. Esta funcionalidad es crítica para analizar anuncios que usan video como medio principal.

## 🎯 Propósito

- Detectar automáticamente archivos de video en datasets
- Extraer frames representativos de cada video
- Optimizar frames para análisis con IA
- Mantener balance entre videos e imágenes estáticas
- Proporcionar contexto narrativo completo de anuncios de video

## 🔧 Implementación Técnica

### Tecnologías Utilizadas

- **OpenCV (cv2)**: Biblioteca de visión por computadora para procesamiento de video
- **Pillow (PIL)**: Procesamiento y optimización de imágenes extraídas
- **NumPy**: Operaciones matemáticas para manipulación de frames
- **Pathlib**: Gestión moderna de rutas de archivos

### Arquitectura

```
Videos en media/ → Detección Multi-Capa → Validación OpenCV → 
Extracción de Frames → Optimización → Almacenamiento → 
Integración en Payload de IA
```

## 🎬 Detección de Videos

### Sistema Multi-Capa

El sistema implementa detección en 3 niveles para garantizar cero falsos positivos:

#### Nivel 1: Detección por Extensión

Identifica videos por extensión de archivo:

```python
video_extensions = [
    '.mp4',   # Formato más común
    '.avi',   # Video antiguo pero común
    '.mov',   # QuickTime (Apple)
    '.mkv',   # Container popular
    '.webm',  # Web optimizado
    '.m4v',   # iTunes/Apple
    '.flv',   # Flash Video
    '.wmv'    # Windows Media
]
```

**Ventajas**:
- Rápido (verificación instantánea)
- Eficiente (no requiere abrir archivo)
- Cubre 99% de casos comunes

**Limitaciones**:
- No detecta videos con extensión incorrecta
- No valida que el archivo sea realmente un video válido

#### Nivel 2: Detección por Tamaño

Si no se encuentran videos por extensión, busca archivos grandes:

```python
# Buscar archivos >100KB que no sean imágenes conocidas
large_files = [
    f for f in all_files 
    if f.suffix.lower() not in image_extensions 
    and f.stat().st_size > 100 * 1024  # >100KB
]
```

**Cuándo se usa**:
- Videos con extensión desconocida
- Videos descargados con nombres incorrectos
- Archivos multimedia sin extensión

**Limitaciones**:
- Puede incluir archivos no-video (PDFs grandes, etc.)
- Requiere validación adicional

#### Nivel 3: Validación con OpenCV

Valida que cada archivo potencial sea realmente un video:

```python
def is_valid_video_file(file_path: Path) -> bool:
    """Verifica si un archivo es un video válido usando OpenCV"""
    # Verificar extensión
    if file_path.suffix.lower() not in video_extensions:
        return False
    
    # Verificar que exista y tenga contenido
    if not file_path.exists() or file_path.stat().st_size == 0:
        return False
    
    # Abrir con OpenCV
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        return False
    
    # Validar propiedades
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    
    # Debe tener al menos 1 frame y FPS > 0
    return frame_count > 0 and fps > 0
```

**Validaciones realizadas**:
- Archivo se puede abrir con OpenCV
- Tiene frames (frame_count > 0)
- Tiene FPS válido (fps > 0)
- No está corrupto o vacío

**Ventajas**:
- Zero falsos positivos
- Detecta videos corruptos
- Valida integridad del archivo

### Logging de Detección

El sistema registra detalladamente cada paso:

```
🎬 PASO 5: Detectando y extrayendo frames de videos...
   🔍 Buscando archivos de video en media/...
   📁 Total archivos en media/: 147
      📹 Detectado por extensión: video1.mp4
      📹 Detectado por extensión: video2.mov
   ✅ Video válido confirmado: video1.mp4
   ✅ Video válido confirmado: video2.mov
   📹 2 videos válidos encontrados, extrayendo frames...
```

## 🎞️ Extracción de Frames

### Estrategia de Distribución Temporal

Los frames no se extraen solo al inicio del video, sino distribuidos estratégicamente:

#### Distribución Equitativa

```python
# Para un video de 100 frames, extrayendo 3 frames:
# Frame 25 (25% del video)
# Frame 50 (50% del video - punto medio)
# Frame 75 (75% del video)
```

**Algoritmo**:
```python
num_frames_to_extract = min(max_frames_per_video, max_video_frames - frames_extracted)

if num_frames_to_extract == 1:
    # Solo un frame: usar el punto medio
    frame_indices = [frame_count // 2]
else:
    # Múltiples frames: distribuir equitativamente
    step = frame_count / (num_frames_to_extract + 1)
    frame_indices = [int(i * step) for i in range(1, num_frames_to_extract + 1)]
```

**Ventajas**:
- Captura evolución narrativa del anuncio
- No pierde información del final del video
- Representa mejor el contenido completo
- Ideal para análisis de storytelling

#### Cálculo Dinámico de Frames

El sistema calcula cuántos frames extraer según:
- Total de videos encontrados
- Límite máximo de frames (40% de 50 = 20 frames)
- Disponibilidad de espacio en el payload

```python
max_frames_per_video = max(1, max_video_frames // max(1, len(valid_video_files)))

# Ejemplo: 4 videos, máximo 20 frames totales
# max_frames_per_video = 20 // 4 = 5 frames por video
```

### Proceso de Extracción

#### Paso 1: Abrir Video

```python
cap = cv2.VideoCapture(str(video_path))

# Validar que se abrió correctamente
if not cap.isOpened():
    logger.warning(f"No se pudo abrir {video_path.name}")
    continue

# Obtener propiedades
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

# Validar propiedades
if frame_count == 0 or fps == 0:
    logger.warning(f"Video inválido: {video_path.name}")
    cap.release()
    continue
```

#### Paso 2: Navegar a Frame Específico

```python
# Navegar a frame específico
cap.set(cv2.CAP_PROP_POS_FRAMES, min(frame_num, frame_count - 1))

# Leer frame
ret, frame = cap.read()

# Validar que se leyó correctamente
if not ret or frame is None:
    continue
```

#### Paso 3: Optimizar Frame

```python
# Redimensionar si es muy grande
h, w = frame.shape[:2]
if max(h, w) > 1920:
    scale = 1920 / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
```

**Interpolación LANCZOS4**:
- Algoritmo de alta calidad
- Preserva detalles importantes
- Evita aliasing y artefactos
- Ideal para redimensionamiento de imágenes

#### Paso 4: Guardar Frame

```python
frame_filename = f"{base_name}_frame{idx:03d}.jpg"
frame_path = video_frames_dir / frame_filename

cv2.imwrite(
    str(frame_path), 
    frame, 
    [cv2.IMWRITE_JPEG_QUALITY, 85]
)
```

**Calidad JPEG 85**:
- Balance perfecto calidad/tamaño
- Reduce tamaño sin pérdida notable
- Optimiza transferencia a OpenAI
- Mantiene detalles suficientes para análisis

### Estructura de Nombres

```
video_frames/
├── video1_frame000.jpg  # Frame 1 del video 1
├── video1_frame001.jpg  # Frame 2 del video 1
├── video1_frame002.jpg  # Frame 3 del video 1
├── video2_frame000.jpg  # Frame 1 del video 2
└── ...
```

**Ventajas del naming**:
- Identifica origen (video de origen)
- Orden secuencial claro
- Fácil de rastrear y depurar
- Compatible con ordenamiento automático

## ⚖️ Balance 40/60 (Videos/Imágenes)

### Proporción Científica

El sistema implementa un balance basado en mejores prácticas:

- **40% Frames de Video** (20 de 50 total): Narrativa, storytelling, evolución temporal
- **60% Imágenes Estáticas** (30 de 50 total): Análisis detallado, composición, diseño

### ¿Por qué esta proporción?

1. **Videos requieren más contexto**: Cada frame muestra un momento, pero necesita múltiples frames para entender la historia completa
2. **Imágenes estáticas son más densas**: Una imagen puede ser analizada completamente en un solo frame
3. **Balance de análisis**: Permite comparar narrativas dinámicas con diseño estático
4. **Optimización de tokens**: Respeta límites de OpenAI mientras maximiza información

### Implementación Dinámica

```python
MAX_IMAGES = 50                    # Total máximo de assets
max_static_images = 30             # 60% = 30 imágenes estáticas
max_video_frames = 20              # 40% = 20 frames de video

# Si se procesan menos frames de video de los esperados:
if total_video_frames < max_video_frames:
    # Ajusta el límite de imágenes estáticas
    remaining_slots = MAX_IMAGES - total_video_frames
    max_static_images = remaining_slots
```

**Ajuste automático**:
- Si hay pocos videos, usa más imágenes estáticas
- Si hay muchos videos, prioriza frames hasta el límite
- Siempre respeta el máximo total de 50 assets

## 📊 Almacenamiento y Reutilización

### Directorio de Frames

```
datasets/facebook/{run_id}/
└── video_frames/
    ├── video1_frame000.jpg
    ├── video1_frame001.jpg
    └── ...
```

### Reutilización de Frames

El sistema verifica si ya existen frames extraídos:

```python
# Verificar si ya existen frames
if video_frames_dir.exists():
    existing_frames = [
        f for f in video_frames_dir.iterdir() 
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']
    ]
    if existing_frames:
        logger.info(f"{len(existing_frames)} frames ya existen, reutilizando")
        has_video_frames = True
```

**Ventajas**:
- Evita reprocesamiento innecesario
- Acelera análisis repetidos
- Ahorra recursos computacionales
- Mantiene consistencia entre análisis

### Validación de Frames Existentes

```python
# Validar que los frames existentes sean válidos
for frame_file in existing_frames:
    try:
        with Image.open(frame_file) as img:
            img.verify()  # Valida integridad
    except Exception:
        # Frame corrupto, eliminar y re-extraer
        frame_file.unlink()
```

## 🔄 Integración con Análisis de IA

### Inclusión en Payload

Los frames se incluyen en el payload de OpenAI junto con imágenes estáticas:

```python
content_blocks.append({
    "type": "image_url",
    "image_url": {
        "url": f"data:image/jpeg;base64,{b64}",
        "detail": "high"
    }
})
```

### Orden de Procesamiento

1. **PRIMERO**: Procesar frames de video (40%)
2. **SEGUNDO**: Procesar imágenes estáticas (60%)

**Razón**: Asegura que los frames de video se incluyan antes de alcanzar el límite total.

### Contexto para IA

El prompt incluye instrucciones específicas para videos:

```
- Contrasta imágenes estáticas con frames de video
- Analiza la evolución narrativa en frames de video
- Identifica hooks visuales en los primeros frames
- Evalúa storytelling en secuencia de frames
```

## ⚠️ Manejo de Errores

### Errores Comunes

1. **Video no se puede abrir**:
   - Archivo corrupto
   - Formato no soportado
   - Permisos insuficientes
   - **Solución**: Registrar y continuar con siguiente video

2. **Video sin frames**:
   - Archivo vacío
   - Formato inválido
   - **Solución**: Validar antes de procesar

3. **FPS o frame_count inválido**:
   - Video corrupto
   - Metadata incorrecta
   - **Solución**: Validar propiedades antes de extraer

4. **Frame no se puede leer**:
   - Frame específico corrupto
   - Error de navegación
   - **Solución**: Intentar siguiente frame o siguiente video

### Logging Detallado

```
🔄 Procesando: video1.mp4
   ✅ Video válido: 300 frames, 30 FPS
   📊 Extrayendo 5 frames distribuidos
   ✅ Frame extraído: video1_frame000.jpg
   ✅ Frame extraído: video1_frame001.jpg
   ...
   ✅ 5 frames extraídos exitosamente
```

## 📈 Performance y Optimización

### Tiempos Típicos

| Cantidad Videos | Frames/Video | Tiempo Total |
|-----------------|--------------|--------------|
| 1-2 | 3-5 | 5-10 segundos |
| 3-5 | 3-5 | 15-30 segundos |
| 5-10 | 2-3 | 30-60 segundos |

### Factores que Afectan Performance

1. **Tamaño del video**: Videos grandes tardan más en procesar
2. **Cantidad de frames a extraer**: Más frames = más tiempo
3. **Resolución**: Videos de alta resolución requieren más procesamiento
4. **Hardware**: CPU y disco afectan velocidad de lectura/escritura

### Optimizaciones Implementadas

1. **Redimensionamiento**: Frames grandes se redimensionan antes de guardar
2. **Calidad JPEG**: Calidad 85 optimiza tamaño sin pérdida notable
3. **Reutilización**: Frames existentes no se re-extraen
4. **Validación temprana**: Videos inválidos se detectan antes de procesar

## 🔍 Troubleshooting

### Problema: No se detectan videos

**Síntomas**:
- Log muestra "No se encontraron videos"
- Balance muestra 0% frames

**Soluciones**:
1. Verificar que los videos estén en `media/`
2. Verificar extensiones soportadas
3. Verificar que OpenCV esté instalado: `pip install opencv-python`
4. Revisar logs de detección

### Problema: Frames no se extraen

**Síntomas**:
- Videos detectados pero 0 frames extraídos
- Error "No se pudieron extraer frames"

**Soluciones**:
1. Verificar que los videos sean válidos (no corruptos)
2. Verificar permisos de escritura en `video_frames/`
3. Verificar espacio en disco
4. Revisar logs detallados de extracción

### Problema: Frames de baja calidad

**Síntomas**:
- Frames borrosos o pixelados
- Pérdida de detalles importantes

**Soluciones**:
1. Aumentar calidad JPEG (cambiar 85 a 95)
2. Evitar redimensionamiento agresivo
3. Verificar que el video original sea de buena calidad

---

**Última actualización**: Noviembre 2025

