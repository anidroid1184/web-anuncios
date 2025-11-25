"""
Run Management Routes
Endpoints para gestionar runs locales (listar, eliminar, cleanup)
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timedelta
import shutil

from ..utils.config import get_facebook_saved_base

router = APIRouter()


@router.get('/runs/list', tags=["Facebook"])
async def list_saved_runs():
    """
    Lista todos los runs guardados localmente con información de tamaño.

    Returns:
        Lista de runs con metadata: run_id, tamaño, archivos, fecha de
        creación
    """
    try:
        base = get_facebook_saved_base()

        if not base.exists():
            return {
                'status': 'success',
                'runs': [],
                'total_runs': 0,
                'total_size_mb': 0
            }

        runs = []
        total_size = 0

        for run_dir in base.iterdir():
            if not run_dir.is_dir():
                continue

            run_id = run_dir.name

            # Calculate size
            size_bytes = sum(
                f.stat().st_size for f in run_dir.rglob('*') if f.is_file()
            )
            size_mb = size_bytes / (1024 * 1024)
            total_size += size_mb

            # Count files
            file_count = sum(1 for f in run_dir.rglob('*') if f.is_file())

            # Creation date
            created = datetime.fromtimestamp(run_dir.stat().st_ctime)

            # Check what files exist
            has_csv = (run_dir / f'{run_id}.csv').exists()
            has_jsonl = (run_dir / f'{run_id}.jsonl').exists()
            has_media = (run_dir / 'media').exists()
            has_prepared = (run_dir / 'prepared').exists()

            media_count = 0
            if has_media:
                media_count = sum(
                    1 for f in (run_dir / 'media').iterdir() if f.is_file()
                )

            runs.append({
                'run_id': run_id,
                'size_mb': round(size_mb, 2),
                'size_bytes': size_bytes,
                'file_count': file_count,
                'created': created.isoformat(),
                'has_csv': has_csv,
                'has_jsonl': has_jsonl,
                'has_media': has_media,
                'media_count': media_count,
                'has_prepared': has_prepared,
                'path': str(run_dir)
            })

        # Sort by size (largest first)
        runs.sort(key=lambda x: x['size_mb'], reverse=True)

        return {
            'status': 'success',
            'runs': runs,
            'total_runs': len(runs),
            'total_size_mb': round(total_size, 2),
            'base_path': str(base)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/runs/{run_id}', tags=["Facebook"])
async def delete_run(run_id: str):
    """
    Elimina un run específico del almacenamiento local.

    Args:
        run_id: ID del run a eliminar

    Returns:
        Información sobre la eliminación: espacio liberado, archivos
        eliminados
    """
    try:
        base = get_facebook_saved_base()
        run_dir = base / run_id

        if not run_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f'Run {run_id} not found'
            )

        # Calculate size before deleting
        size_bytes = sum(
            f.stat().st_size for f in run_dir.rglob('*') if f.is_file()
        )
        size_mb = size_bytes / (1024 * 1024)

        file_count = sum(1 for f in run_dir.rglob('*') if f.is_file())

        # Delete entire directory
        shutil.rmtree(run_dir)

        return {
            'status': 'success',
            'message': f'Run {run_id} deleted successfully',
            'run_id': run_id,
            'freed_space_mb': round(size_mb, 2),
            'files_deleted': file_count
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/runs/cleanup', tags=["Facebook"])
async def cleanup_runs(
    keep_latest: int = 1,
    min_size_mb: Optional[float] = None,
    older_than_days: Optional[int] = None
):
    """
    Limpia datasets antiguos según criterios.

    Args:
        keep_latest: Mantener los N runs más recientes (default: 1)
        min_size_mb: Solo eliminar runs mayores a este tamaño en MB
        older_than_days: Solo eliminar runs más antiguos que N días

    Returns:
        Lista de runs eliminados y espacio liberado
    """
    try:
        base = get_facebook_saved_base()

        if not base.exists():
            return {
                'status': 'success',
                'message': 'No runs found',
                'deleted_runs': [],
                'total_freed_mb': 0
            }

        # Get all runs
        all_runs = []
        for run_dir in base.iterdir():
            if not run_dir.is_dir():
                continue

            run_id = run_dir.name
            size_bytes = sum(
                f.stat().st_size for f in run_dir.rglob('*') if f.is_file()
            )
            size_mb = size_bytes / (1024 * 1024)
            created = datetime.fromtimestamp(run_dir.stat().st_ctime)

            all_runs.append({
                'run_id': run_id,
                'path': run_dir,
                'size_mb': size_mb,
                'size_bytes': size_bytes,
                'created': created
            })

        # Sort by date (most recent first)
        all_runs.sort(key=lambda x: x['created'], reverse=True)

        # Determine which to delete
        to_delete = []

        for i, run in enumerate(all_runs):
            # Keep the N most recent
            if i < keep_latest:
                continue

            # Filter by minimum size
            if min_size_mb and run['size_mb'] < min_size_mb:
                continue

            # Filter by age
            if older_than_days:
                age_days = (datetime.now() - run['created']).days
                if age_days < older_than_days:
                    continue

            to_delete.append(run)

        # Delete selected runs
        deleted = []
        total_freed = 0

        for run in to_delete:
            try:
                file_count = sum(
                    1 for f in run['path'].rglob('*') if f.is_file()
                )
                shutil.rmtree(run['path'])

                deleted.append({
                    'run_id': run['run_id'],
                    'freed_mb': round(run['size_mb'], 2),
                    'files_deleted': file_count,
                    'created': run['created'].isoformat()
                })
                total_freed += run['size_mb']
            except Exception as e:
                deleted.append({
                    'run_id': run['run_id'],
                    'error': str(e)
                })

        msg_part1 = f'Deleted {len(deleted)} runs,'
        msg_part2 = f'freed {round(total_freed, 2)} MB'
        message = f'{msg_part1} {msg_part2}'

        return {
            'status': 'success',
            'message': message,
            'deleted_runs': deleted,
            'kept_runs': len(all_runs) - len(deleted),
            'total_freed_mb': round(total_freed, 2),
            'criteria': {
                'keep_latest': keep_latest,
                'min_size_mb': min_size_mb,
                'older_than_days': older_than_days
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
