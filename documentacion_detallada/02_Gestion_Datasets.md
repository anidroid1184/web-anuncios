# 02. Gestión de Datasets

## 📋 Descripción General

El sistema incluye funcionalidades completas para gestionar datasets descargados de Facebook Ads Library. Permite listar, consultar, descargar, eliminar y limpiar datasets de forma eficiente.

## 🎯 Propósito

- Organizar y gestionar múltiples datasets descargados
- Facilitar el acceso a datos históricos
- Optimizar el uso de espacio en disco
- Mantener trazabilidad de análisis realizados
- Reutilizar datasets para múltiples análisis

## 📁 Estructura de Datasets

### Organización de Archivos

```
api_service/app/processors/datasets/saved_datasets/facebook/
├── {run_id_1}/
│   ├── {run_id_1}.csv
│   ├── {run_id_1}.jsonl
│   ├── media/
│   │   ├── imagen1.jpg
│   │   ├── video1.mp4
│   │   └── ...
│   ├── video_frames/
│   │   └── ...
│   └── reports/
│       └── ...
├── {run_id_2}/
│   └── ...
└── ...
```

### Componentes de un Dataset

1. **CSV**: Metadatos estructurados en formato tabular
2. **JSONL**: Datos en formato JSON línea por línea
3. **media/**: Archivos multimedia descargados (imágenes y videos)
4. **video_frames/**: Frames extraídos de videos (si se procesaron)
5. **reports/**: Reportes generados de análisis (PDF, JSON)

## 📡 Endpoints Disponibles

### GET `/api/v1/apify/facebook/runs/list`

Lista todos los datasets disponibles localmente.

#### Respuesta

```json
{
  "status": "success",
  "total_runs": 5,
  "runs": [
    {
      "run_id": "bfMXWLphPQcDmBsrz",
      "path": "D:/.../datasets/facebook/bfMXWLphPQcDmBsrz",
      "has_csv": true,
      "has_jsonl": true,
      "has_media": true,
      "media_count": 147,
      "created_at": "2025-11-24T10:30:00",
      "size_bytes": 15728640
    }
  ]
}
```

#### Uso

```bash
curl "http://localhost:8001/api/v1/apify/facebook/runs/list"
```

**Casos de uso**:
- Ver qué datasets están disponibles
- Verificar tamaño de almacenamiento usado
- Identificar datasets para análisis
- Auditoría de almacenamiento

### GET `/api/v1/apify/facebook/runs/{run_id}`

Obtiene información detallada de un dataset específico.

#### Respuesta

```json
{
  "status": "success",
  "run_id": "bfMXWLphPQcDmBsrz",
  "exists": true,
  "path": "D:/.../datasets/facebook/bfMXWLphPQcDmBsrz",
  "files": {
    "csv": {
      "exists": true,
      "path": "bfMXWLphPQcDmBsrz.csv",
      "size_bytes": 245760,
      "rows": 147
    },
    "jsonl": {
      "exists": true,
      "path": "bfMXWLphPQcDmBsrz.jsonl",
      "size_bytes": 512000,
      "lines": 147
    },
    "media": {
      "exists": true,
      "path": "media/",
      "count": 147,
      "size_bytes": 15728640,
      "images": 143,
      "videos": 4
    },
    "video_frames": {
      "exists": true,
      "path": "video_frames/",
      "count": 12,
      "size_bytes": 1048576
    },
    "reports": {
      "exists": true,
      "path": "reports/",
      "files": [
        "Reporte_Analisis_Completo_bfMXWLphPQcDmBsrz.pdf",
        "bfMXWLphPQcDmBsrz_analysis_complete.json"
      ]
    }
  },
  "total_size_bytes": 17510400,
  "created_at": "2025-11-24T10:30:00",
  "last_modified": "2025-11-24T11:45:00"
}
```

#### Uso

```bash
curl "http://localhost:8001/api/v1/apify/facebook/runs/bfMXWLphPQcDmBsrz"
```

**Información proporcionada**:
- Estado de cada componente del dataset
- Tamaños de archivos
- Cantidad de anuncios (filas en CSV)
- Cantidad de archivos multimedia
- Fechas de creación y modificación

### DELETE `/api/v1/apify/facebook/runs/{run_id}`

Elimina un dataset completo del sistema.

#### ⚠️ ADVERTENCIA

Esta operación es **IRREVERSIBLE**. Eliminará:
- CSV y JSONL
- Directorio media/ completo
- Frames de video
- Reportes generados

#### Respuesta

```json
{
  "status": "success",
  "message": "Run bfMXWLphPQcDmBsrz eliminado exitosamente",
  "deleted_path": "D:/.../datasets/facebook/bfMXWLphPQcDmBsrz",
  "freed_space_bytes": 17510400
}
```

#### Uso

```bash
curl -X DELETE "http://localhost:8001/api/v1/apify/facebook/runs/bfMXWLphPQcDmBsrz"
```

**Mejores prácticas**:
- Verifica primero con `GET /runs/{run_id}` antes de eliminar
- Considera hacer backup de datasets importantes
- Usa limpieza automática para datasets antiguos en lugar de eliminación manual

### POST `/api/v1/apify/facebook/runs/cleanup`

Elimina automáticamente datasets antiguos según criterios configurables.

#### Parámetros

```json
{
  "days_old": 30,
  "keep_recent": 10,
  "dry_run": false
}
```

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `days_old` | integer | 30 | Eliminar datasets más antiguos que X días |
| `keep_recent` | integer | 10 | Siempre mantener los N datasets más recientes |
| `dry_run` | boolean | false | Si `true`, solo simula sin eliminar |

#### Respuesta

```json
{
  "status": "success",
  "dry_run": false,
  "criteria": {
    "days_old": 30,
    "keep_recent": 10
  },
  "runs_checked": 15,
  "runs_to_delete": 3,
  "runs_deleted": 3,
  "runs_kept": 12,
  "freed_space_bytes": 52428800,
  "deleted_runs": [
    {
      "run_id": "old_run_1",
      "days_old": 45,
      "size_bytes": 15728640
    }
  ]
}
```

#### Uso

```bash
# Primero simular (recomendado)
curl -X POST "http://localhost:8001/api/v1/apify/facebook/runs/cleanup" \
  -H "Content-Type: application/json" \
  -d '{
    "days_old": 30,
    "keep_recent": 10,
    "dry_run": true
  }'

# Luego ejecutar si está bien
curl -X POST "http://localhost:8001/api/v1/apify/facebook/runs/cleanup" \
  -H "Content-Type: application/json" \
  -d '{
    "days_old": 30,
    "keep_recent": 10,
    "dry_run": false
  }'
```

**Estrategias de limpieza**:
- **Conservadora**: `days_old=60, keep_recent=20`
- **Moderada**: `days_old=30, keep_recent=10` (recomendado)
- **Agresiva**: `days_old=7, keep_recent=5`

### POST `/api/v1/apify/facebook/download-dataset-from-run`

Descarga un dataset desde Apify si no existe localmente.

#### Parámetros

```json
{
  "run_id": "bfMXWLphPQcDmBsrz",
  "download_media": true,
  "force_download": false
}
```

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `run_id` | string | - | Run ID a descargar desde Apify |
| `download_media` | boolean | true | Si descargar archivos multimedia |
| `force_download` | boolean | false | Si `true`, re-descarga incluso si existe |

#### Respuesta

```json
{
  "status": "success",
  "run_id": "bfMXWLphPQcDmBsrz",
  "message": "Dataset descargado exitosamente",
  "downloaded": {
    "csv": true,
    "jsonl": true,
    "media": true,
    "media_count": 147
  },
  "path": "D:/.../datasets/facebook/bfMXWLphPQcDmBsrz",
  "size_bytes": 17510400
}
```

#### Uso

```bash
curl -X POST "http://localhost:8001/api/v1/apify/facebook/download-dataset-from-run" \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "bfMXWLphPQcDmBsrz",
    "download_media": true
  }'
```

**Cuándo usar**:
- Recuperar dataset eliminado accidentalmente
- Descargar dataset en otra máquina
- Actualizar dataset con media faltante
- Migrar datasets entre servidores

## 🔄 Flujos de Trabajo

### Flujo 1: Auditoría de Almacenamiento

```python
import requests

# 1. Listar todos los datasets
response = requests.get("http://localhost:8001/api/v1/apify/facebook/runs/list")
data = response.json()

total_size = sum(run["size_bytes"] for run in data["runs"])
print(f"Total datasets: {data['total_runs']}")
print(f"Espacio total usado: {total_size / (1024**3):.2f} GB")

# 2. Identificar datasets grandes
large_runs = [r for r in data["runs"] if r["size_bytes"] > 100 * 1024 * 1024]
print(f"Datasets >100MB: {len(large_runs)}")
```

### Flujo 2: Limpieza Automática Programada

```python
import requests
import schedule
import time

def cleanup_old_datasets():
    """Ejecuta limpieza automática cada semana"""
    response = requests.post(
        "http://localhost:8001/api/v1/apify/facebook/runs/cleanup",
        json={
            "days_old": 30,
            "keep_recent": 10,
            "dry_run": False
        }
    )
    result = response.json()
    print(f"Limpieza completada: {result['freed_space_bytes'] / (1024**2):.2f} MB liberados")

# Programar ejecución semanal
schedule.every().week.do(cleanup_old_datasets)

while True:
    schedule.run_pending()
    time.sleep(3600)  # Verificar cada hora
```

### Flujo 3: Verificación de Integridad

```python
import requests

def verify_dataset_integrity(run_id):
    """Verifica que un dataset esté completo"""
    response = requests.get(
        f"http://localhost:8001/api/v1/apify/facebook/runs/{run_id}"
    )
    
    if response.status_code == 404:
        return False, "Dataset no encontrado"
    
    data = response.json()
    files = data["files"]
    
    checks = {
        "CSV": files["csv"]["exists"],
        "JSONL": files["jsonl"]["exists"],
        "Media": files["media"]["exists"],
    }
    
    all_ok = all(checks.values())
    return all_ok, checks

# Verificar dataset específico
ok, details = verify_dataset_integrity("bfMXWLphPQcDmBsrz")
print(f"Integridad: {'OK' if ok else 'FALLO'}")
print(f"Detalles: {details}")
```

### Flujo 4: Migración de Datasets

```python
import requests

def download_dataset_for_migration(run_id, download_media=True):
    """Descarga dataset desde Apify para migración"""
    response = requests.post(
        "http://localhost:8001/api/v1/apify/facebook/download-dataset-from-run",
        json={
            "run_id": run_id,
            "download_media": download_media,
            "force_download": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Dataset descargado: {data['size_bytes'] / (1024**2):.2f} MB")
        return True
    else:
        print(f"Error: {response.json()['detail']}")
        return False

# Migrar lista de datasets
run_ids_to_migrate = ["run1", "run2", "run3"]
for run_id in run_ids_to_migrate:
    download_dataset_for_migration(run_id)
```

## 📊 Gestión de Espacio en Disco

### Estimación de Tamaños

| Componente | Tamaño Típico | Por Anuncio |
|------------|---------------|-------------|
| CSV | 1-5 KB | ~3 KB |
| JSONL | 3-10 KB | ~5 KB |
| Imagen | 50-500 KB | ~150 KB |
| Video | 1-10 MB | ~3 MB |
| Frame de video | 50-200 KB | ~100 KB |

**Ejemplo**: Dataset con 100 anuncios (90 imágenes, 10 videos):
- CSV: ~300 KB
- JSONL: ~500 KB
- Imágenes: ~13.5 MB
- Videos: ~30 MB
- Frames (30 frames): ~3 MB
- **Total**: ~47 MB

### Estrategias de Optimización

1. **Descarga selectiva de media**: Solo descargar media cuando se necesite para análisis
2. **Compresión de videos**: Comprimir videos grandes antes de almacenar
3. **Eliminación de duplicados**: Identificar y eliminar archivos duplicados
4. **Limpieza automática**: Programar limpieza regular de datasets antiguos
5. **Almacenamiento externo**: Mover datasets antiguos a almacenamiento externo

## ⚙️ Configuración

### Variables de Entorno

```env
# Directorio base para datasets
DATA_DIR=data

# Directorio específico para datasets de Facebook
DATASETS_DIR=data/datasets/facebook
```

### Límites Recomendados

- **Espacio mínimo**: 10 GB para desarrollo
- **Espacio recomendado**: 50+ GB para producción
- **Retención de datos**: 30-60 días (ajustable)
- **Datasets a mantener**: 10-20 más recientes

## 🔍 Troubleshooting

### Problema: Dataset no encontrado

**Síntoma**: `GET /runs/{run_id}` retorna 404

**Soluciones**:
1. Verificar que el Run ID sea correcto
2. Listar todos los runs con `GET /runs/list`
3. Descargar desde Apify si existe allí
4. Verificar permisos del directorio

### Problema: No se puede eliminar dataset

**Síntoma**: `DELETE /runs/{run_id}` falla

**Soluciones**:
1. Verificar permisos de escritura
2. Cerrar procesos que usen los archivos
3. Verificar que no esté bloqueado por otro proceso
4. Intentar eliminar manualmente el directorio

### Problema: Descarga falla o es lenta

**Síntoma**: `POST /download-dataset-from-run` tarda mucho o falla

**Soluciones**:
1. Verificar conexión a internet
2. Verificar token de Apify
3. Reducir `download_media` si solo necesitas metadatos
4. Descargar en horarios de menor tráfico
5. Verificar espacio disponible en disco

## 📈 Métricas y Monitoreo

### Métricas Clave

- **Total de datasets**: Cantidad de runs almacenados
- **Espacio usado**: Tamaño total en disco
- **Espacio disponible**: Espacio libre restante
- **Tasa de crecimiento**: MB/día de nuevos datos
- **Tasa de limpieza**: MB liberados por limpieza

### Dashboard Recomendado

```python
def get_storage_metrics():
    """Obtiene métricas de almacenamiento"""
    response = requests.get("http://localhost:8001/api/v1/apify/facebook/runs/list")
    data = response.json()
    
    total_size = sum(r["size_bytes"] for r in data["runs"])
    avg_size = total_size / data["total_runs"] if data["total_runs"] > 0 else 0
    
    return {
        "total_runs": data["total_runs"],
        "total_size_gb": total_size / (1024**3),
        "avg_size_mb": avg_size / (1024**2),
        "oldest_run_days": calculate_oldest_age(data["runs"]),
        "newest_run_days": calculate_newest_age(data["runs"])
    }
```

---

**Última actualización**: Noviembre 2025

