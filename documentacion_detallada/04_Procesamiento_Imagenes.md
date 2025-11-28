# 04. Procesamiento de Imágenes Estáticas

## 📋 Descripción General

El sistema procesa y optimiza imágenes estáticas de anuncios para análisis con IA. Incluye validación, conversión de formatos, redimensionamiento inteligente y compresión optimizada para garantizar calidad y eficiencia.

## 🎯 Propósito

- Validar integridad de imágenes descargadas
- Convertir formatos especiales a estándar RGB
- Optimizar tamaño para transferencia a OpenAI
- Mantener calidad suficiente para análisis detallado
- Garantizar compatibilidad universal

## 🔧 Implementación Técnica

### Tecnologías Utilizadas

- **Pillow (PIL)**: Procesamiento de imágenes principal
- **Base64**: Codificación para transferencia
- **BytesIO**: Manejo de imágenes en memoria
- **Pathlib**: Gestión moderna de rutas

### Arquitectura

```
Imágenes en media/ → Filtrado por Extensión → 
Validación de Integridad → Conversión de Formato → 
Redimensionamiento → Compresión → 
Codificación Base64 → Payload para IA
```

## 🖼️ Detección y Filtrado

### Formatos Soportados

```python
image_extensions = [
    '.jpg',   # JPEG (más común)
    '.jpeg',  # JPEG alternativo
    '.png',   # PNG con transparencia
    '.webp',  # Web optimizado
    '.gif',   # GIF animado/estático
    '.bmp'    # Bitmap
]
```

### Filtrado Inteligente

El sistema excluye explícitamente extensiones de video para evitar duplicados:

```python
image_files = [
    f for f in media_dir.iterdir() 
    if f.is_file() 
    and f.suffix.lower() in image_extensions
    and f.suffix.lower() not in ['.mp4', '.avi', '.mov', ...]  # Excluir videos
]
```

**Ventajas**:
- Evita procesar videos como imágenes
- Reduce falsos positivos
- Optimiza tiempo de procesamiento
- Claridad en tipo de media procesada

### Ordenamiento Inteligente

Las imágenes se ordenan por tamaño de archivo (prioriza calidad):

```python
image_files = sorted(image_files, key=lambda x: x.stat().st_size, reverse=True)
```

**Ventajas**:
- Procesa primero imágenes de mayor calidad
- Maximiza información enviada a IA
- Mejor análisis con imágenes de alta resolución

## ✅ Validación de Integridad

### Verificación con PIL

```python
try:
    with Image.open(img_file) as img:
        # Validar que sea realmente una imagen válida
        img.verify()
except Exception as e:
    logger.warning(f"Imagen inválida: {img_file.name}: {e}")
    continue  # Continuar con siguiente imagen
```

**Validaciones realizadas**:
- Archivo puede ser abierto por PIL
- Formato es válido y reconocible
- No está corrupto
- Metadata es legible

**Importante**: `verify()` cierra la imagen, por lo que se debe reabrir para procesamiento.

### Manejo de Errores

El sistema continúa procesando aunque una imagen falle:

```python
for img_file in image_files:
    try:
        # Procesar imagen
        process_image(img_file)
    except Exception as e:
        logger.warning(f"Error procesando {img_file.name}: {e}")
        # Continuar con siguiente imagen sin detener el proceso
        continue
```

## 🔄 Conversión de Formatos

### Formatos Especiales

Algunos formatos requieren conversión antes de procesar:

```python
if img.mode in ('RGBA', 'P', 'LA'):
    img = img.convert('RGB')
```

#### RGBA (Red, Green, Blue, Alpha)
- **Descripción**: Imagen con canal de transparencia
- **Problema**: OpenAI no siempre maneja bien la transparencia
- **Solución**: Convertir a RGB (perdiendo canal alpha pero manteniendo colores)

#### P (Palette)
- **Descripción**: Imagen indexada con paleta de colores
- **Problema**: Formato antiguo, puede tener problemas
- **Solución**: Convertir a RGB para formato universal

#### LA (Luminance, Alpha)
- **Descripción**: Escala de grises con transparencia
- **Problema**: Formato poco común
- **Solución**: Convertir a RGB para consistencia

### Conversión a RGB

RGB es el estándar universal:
- Compatible con todos los sistemas
- Sin pérdida de información de color (excepto transparencia)
- Optimizado para procesamiento
- Ideal para análisis visual

## 📐 Redimensionamiento Inteligente

### Algoritmo de Redimensionamiento

```python
# Redimensionar si es muy grande (optimizar para OpenAI)
if max(img.size) > 800:
    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
```

### ¿Por qué 800px?

1. **Límites de OpenAI**: OpenAI acepta imágenes grandes, pero hay límites prácticos
2. **Balance calidad/tamaño**: 800px mantiene detalles suficientes para análisis
3. **Optimización de tokens**: Imágenes más pequeñas usan menos tokens
4. **Velocidad**: Transferencia más rápida de datos más pequeños

### Algoritmo LANCZOS

```python
Image.Resampling.LANCZOS  # También conocido como LANCZOS3
```

**Características**:
- Algoritmo de alta calidad
- Preserva detalles importantes
- Evita aliasing y artefactos
- Ideal para reducción de tamaño

**Comparación con otros algoritmos**:
- **NEAREST**: Rápido pero baja calidad (pixelado)
- **BILINEAR**: Rápido, calidad media
- **BICUBIC**: Balance calidad/velocidad
- **LANCZOS**: Máxima calidad, más lento (recomendado)

### Mantenimiento de Aspect Ratio

`thumbnail()` mantiene automáticamente el aspect ratio:

```python
# Imagen 1920x1080 → Redimensiona a 800x450 (mantiene 16:9)
# Imagen 3000x2000 → Redimensiona a 800x533 (mantiene 3:2)
```

**Ventajas**:
- No distorsiona la imagen
- Preserva composición original
- Mejor para análisis de diseño

## 🗜️ Compresión JPEG

### Configuración de Calidad

```python
buffered = BytesIO()
img.save(buffered, format="JPEG", quality=85, optimize=True)
```

### Calidad 85: ¿Por qué?

**Balance Perfecto**:
- **Calidad 80-90**: Rango óptimo para web
- **Calidad 85**: Balance específico probado
- **Pérdida visual**: Imperceptible para análisis
- **Reducción de tamaño**: ~50-70% del original

### Comparación de Calidades

| Calidad | Tamaño | Calidad Visual | Uso Recomendado |
|---------|--------|----------------|-----------------|
| 50 | Muy pequeño | Baja, artefactos visibles | No recomendado |
| 70 | Pequeño | Media, algunos artefactos | Web rápido |
| 85 | Medio | Alta, artefactos imperceptibles | **Análisis IA** |
| 95 | Grande | Muy alta, sin artefactos | Archivado |
| 100 | Muy grande | Sin pérdida | No recomendado (tamaño)

### Optimización Automática

```python
optimize=True
```

**Efecto**:
- Optimiza tablas Huffman
- Reduce tamaño adicional ~5-10%
- Sin pérdida de calidad
- Procesamiento adicional mínimo

## 💾 Codificación Base64

### Proceso de Codificación

```python
# 1. Guardar imagen optimizada en buffer en memoria
buffered = BytesIO()
img.save(buffered, format="JPEG", quality=85, optimize=True)

# 2. Obtener bytes
image_bytes = buffered.getvalue()

# 3. Codificar a Base64
b64 = base64.b64encode(image_bytes).decode('utf-8')

# 4. Crear URL data para OpenAI
data_url = f"data:image/jpeg;base64,{b64}"
```

### ¿Por qué Base64?

**Ventajas**:
1. **Seguridad**: Los datos no salen del servidor
2. **Confiabilidad**: No depende de servidores externos
3. **Velocidad**: Elimina latencia de descarga de imágenes
4. **Simplicidad**: No requiere configuración adicional (ngrok, servidores HTTP)

**Desventajas**:
- Aumenta tamaño ~33% (Base64 encoding overhead)
- Payload más grande que URLs
- Pero: Beneficios superan desventajas

### Formato Data URL

```
data:image/jpeg;base64,{base64_encoded_data}
```

**Componentes**:
- `data:`: Esquema de data URL
- `image/jpeg`: MIME type
- `base64`: Método de codificación
- `{data}`: Datos codificados

## ⚖️ Balance 60% Imágenes Estáticas

### Proporción en el Sistema

```python
MAX_IMAGES = 50                    # Total máximo de assets
max_static_images = 30             # 60% = 30 imágenes estáticas
max_video_frames = 20              # 40% = 20 frames de video
```

### Ajuste Dinámico

Si hay menos frames de video de los esperados:

```python
if total_video_frames > 0:
    # Si tenemos frames, ajustar el límite de imágenes estáticas
    remaining_slots = MAX_IMAGES - total_video_frames
    max_static_images = min(max_static_images, remaining_slots)
```

**Ejemplo**:
- Total: 50 assets máximo
- Frames de video procesados: 15 (en lugar de 20)
- Ajuste: Imágenes estáticas pueden usar 35 slots (50 - 15)
- Pero se respeta máximo de 30 para mantener balance

### Límite de Procesamiento

```python
for img_file in image_files:
    if total_imgs >= max_static_images:
        logger.info(f"Límite de {max_static_images} imágenes alcanzado")
        break
```

**Ventajas del límite**:
- Controla tamaño del payload
- Respeta límites de OpenAI
- Optimiza costos de API
- Mantiene tiempo de procesamiento razonable

## 📊 Estadísticas de Procesamiento

### Logging Detallado

```
🖼️  PASO 6.2: Procesando hasta 30 imágenes estáticas...
   📊 147 imágenes estáticas encontradas
   ✓ Procesadas 10 imágenes...
   ✓ Procesadas 20 imágenes...
   ✓ Procesadas 30 imágenes...
   ⚠️  Límite de 30 imágenes alcanzado
   ✅ Total imágenes estáticas procesadas: 30/30
```

### Métricas Capturadas

- Total de imágenes encontradas
- Imágenes procesadas exitosamente
- Imágenes que fallaron (con razón)
- Tamaño promedio de imágenes
- Tiempo de procesamiento

## ⚠️ Manejo de Errores

### Errores Comunes

1. **Imagen corrupta**:
   - Archivo dañado durante descarga
   - **Solución**: `verify()` detecta y se omite

2. **Formato no soportado**:
   - Formato desconocido por PIL
   - **Solución**: Se omite con warning

3. **Imagen muy grande**:
   - Consume demasiada memoria
   - **Solución**: Redimensionamiento automático

4. **Error de conversión**:
   - Fallo al convertir formato
   - **Solución**: Se omite y continúa

### Robustez del Sistema

El sistema es **tolerante a fallos**:
- Una imagen que falla no detiene el proceso
- Se registran todos los errores
- Se continúa con siguiente imagen
- Se reporta estadísticas finales

## 📈 Performance y Optimización

### Tiempos Típicos

| Cantidad Imágenes | Tiempo Total |
|-------------------|--------------|
| 10 | 2-5 segundos |
| 30 | 5-15 segundos |
| 50 | 10-25 segundos |
| 100+ | 20-60 segundos |

### Factores que Afectan Performance

1. **Tamaño de imágenes**: Imágenes grandes tardan más en procesar
2. **Cantidad total**: Más imágenes = más tiempo
3. **Conversiones necesarias**: RGBA/P/LA requieren conversión adicional
4. **Hardware**: CPU y RAM afectan velocidad

### Optimizaciones Implementadas

1. **Procesamiento en memoria**: Usa BytesIO para evitar escritura a disco
2. **Redimensionamiento temprano**: Reduce tamaño antes de codificar
3. **Compresión optimizada**: JPEG calidad 85 balance perfecto
4. **Paralelización potencial**: Estructura permite procesamiento paralelo futuro

## 🔍 Troubleshooting

### Problema: Imágenes no se procesan

**Síntomas**:
- Log muestra "0 imágenes procesadas"
- Error en procesamiento

**Soluciones**:
1. Verificar que las imágenes estén en `media/`
2. Verificar extensiones soportadas
3. Verificar permisos de lectura
4. Revisar logs de errores específicos

### Problema: Imágenes de baja calidad

**Síntomas**:
- Imágenes pixeladas o borrosas
- Pérdida de detalles importantes

**Soluciones**:
1. Aumentar límite de redimensionamiento (800 → 1200)
2. Aumentar calidad JPEG (85 → 95)
3. Verificar calidad de imágenes originales

### Problema: Procesamiento muy lento

**Síntomas**:
- Tarda mucho en procesar imágenes
- Sistema se queda sin recursos

**Soluciones**:
1. Reducir cantidad de imágenes procesadas
2. Optimizar tamaño de redimensionamiento
3. Verificar recursos del sistema (RAM, CPU)

---

**Última actualización**: Noviembre 2025

