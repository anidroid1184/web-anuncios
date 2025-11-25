"""
Módulo de Datasets - Gestión de datasets locales
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import shutil
from datetime import datetime
from .utils import get_facebook_saved_base

router = APIRouter()


@router.get("/runs/list", tags=["datasets"])
async def list_saved_runs():
    """
    Lista todos los runs guardados localmente con información de tamaño.

    Returns:
        {
            "status": "success",
            "runs": [
                {
                    "run_id": "...",
                    "size_mb": ...,
                    "file_count": ...,
                    "created": "...",
                    "has_media": bool,
                    "has_prepared": bool
                }
            ]
        }
    """
    try:
        saved_base = get_facebook_saved_base()
        if not saved_base.exists():
            return {"status": "success", "runs": []}

        runs = []
        for run_dir in saved_base.iterdir():
            if not run_dir.is_dir() or run_dir.name.startswith('.'):
                continue

            # Calcular tamaño
            total_size = sum(
                f.stat().st_size
                for f in run_dir.rglob('*') if f.is_file()
            )

            # Contar archivos
            file_count = sum(1 for f in run_dir.rglob('*') if f.is_file())

            # Verificar carpetas
            has_media = (run_dir / 'media').exists()
            has_prepared = (run_dir / 'prepared').exists()

            # Fecha de creación
            created = datetime.fromtimestamp(
                run_dir.stat().st_mtime
            ).isoformat()

            runs.append({
                'run_id': run_dir.name,
                'size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'created': created,
                'has_media': has_media,
                'has_prepared': has_prepared
            })

        # Ordenar por fecha (más reciente primero)
        runs.sort(key=lambda x: x['created'], reverse=True)

        return {
            'status': 'success',
            'runs': runs,
            'total_runs': len(runs),
            'total_size_mb': round(sum(r['size_mb'] for r in runs), 2)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/runs/{run_id}", tags=["datasets"])
async def delete_run(run_id: str):
    """
    Elimina un run específico y todos sus archivos.

    Args:
        run_id: ID del run a eliminar

    Returns:
        {
            "status": "success",
            "run_id": "...",
            "freed_space_mb": ...
        }
    """
    try:
        saved_base = get_facebook_saved_base()
        run_dir = saved_base / run_id

        if not run_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Run not found: {run_id}"
            )

        # Calcular tamaño antes de eliminar
        total_size = sum(
            f.stat().st_size
            for f in run_dir.rglob('*') if f.is_file()
        )
        freed_mb = total_size / (1024 * 1024)

        # Eliminar directorio
        shutil.rmtree(run_dir)

        return {
            'status': 'success',
            'run_id': run_id,
            'freed_space_mb': round(freed_mb, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runs/cleanup", tags=["datasets"])
async def cleanup_runs(
    keep_latest: Optional[int] = Query(
        None,
        ge=1,
        description="Mantener N runs más recientes"
    ),
    min_size_mb: Optional[float] = Query(
        None,
        ge=0,
        description="Eliminar runs mayores a N MB"
    ),
    older_than_days: Optional[int] = Query(
        None,
        ge=1,
        description="Eliminar runs más antiguos que N días"
    )
):
    """
    Limpieza automática de runs con filtros opcionales.

    Args:
        keep_latest: Mantener solo los N runs más recientes
        min_size_mb: Eliminar runs mayores a este tamaño
        older_than_days: Eliminar runs más antiguos que N días

    Returns:
        {
            "status": "success",
            "deleted_runs": [...],
            "kept_runs": [...],
            "freed_space_mb": ...
        }
    """
    try:
        saved_base = get_facebook_saved_base()
        if not saved_base.exists():
            return {
                'status': 'success',
                'deleted_runs': [],
                'kept_runs': [],
                'freed_space_mb': 0
            }

        # Obtener todos los runs
        all_runs = []
        for run_dir in saved_base.iterdir():
            if not run_dir.is_dir() or run_dir.name.startswith('.'):
                continue

            total_size = sum(
                f.stat().st_size
                for f in run_dir.rglob('*') if f.is_file()
            )

            all_runs.append({
                'run_id': run_dir.name,
                'path': run_dir,
                'size_mb': total_size / (1024 * 1024),
                'created': datetime.fromtimestamp(run_dir.stat().st_mtime)
            })

        # Ordenar por fecha (más reciente primero)
        all_runs.sort(key=lambda x: x['created'], reverse=True)

        # Aplicar filtros
        runs_to_delete = []
        runs_to_keep = []

        for idx, run in enumerate(all_runs):
            should_delete = False

            # Filtro: mantener solo N más recientes
            if keep_latest is not None and idx >= keep_latest:
                should_delete = True

            # Filtro: eliminar por tamaño
            if min_size_mb is not None and run['size_mb'] >= min_size_mb:
                should_delete = True

            # Filtro: eliminar por antigüedad
            if older_than_days is not None:
                days_old = (
                    datetime.now() - run['created']
                ).days
                if days_old >= older_than_days:
                    should_delete = True

            if should_delete:
                runs_to_delete.append(run)
            else:
                runs_to_keep.append(run)

        # Eliminar runs
        total_freed = 0
        deleted_ids = []

        for run in runs_to_delete:
            shutil.rmtree(run['path'])
            total_freed += run['size_mb']
            deleted_ids.append(run['run_id'])

        return {
            'status': 'success',
            'deleted_runs': deleted_ids,
            'kept_runs': [r['run_id'] for r in runs_to_keep],
            'freed_space_mb': round(total_freed, 2),
            'remaining_runs': len(runs_to_keep)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
