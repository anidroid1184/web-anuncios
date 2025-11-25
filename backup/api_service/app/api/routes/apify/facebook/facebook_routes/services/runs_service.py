"""
Facebook Routes - Servicio de Gestión de Runs
Maneja listado, eliminación y limpieza de runs guardados
"""

from typing import Dict, List, Optional
from pathlib import Path
import shutil
from datetime import datetime
from ..config import path_resolver


class RunsService:
    """
    Servicio para gestionar runs guardados localmente.
    Aplica Single Responsibility Principle.
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Inicializa el servicio con la ruta base de datasets.

        Args:
            base_path: Ruta base opcional. Si no se provee,
                      usa path_resolver
        """
        self.base_path = base_path or path_resolver.get_facebook_saved_base()

    def list_saved_runs(self) -> List[Dict]:
        """
        Lista todos los runs guardados con su metadata.

        Returns:
            Lista de diccionarios con información de cada run
        """
        runs = []

        if not self.base_path.exists():
            return runs

        for run_dir in self.base_path.iterdir():
            if not run_dir.is_dir():
                continue

            run_info = self._get_run_info(run_dir)
            if run_info:
                runs.append(run_info)

        # Ordenar por fecha de creación (más reciente primero)
        runs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return runs

    def _get_run_info(self, run_dir: Path) -> Optional[Dict]:
        """
        Extrae información de un directorio de run.

        Args:
            run_dir: Path al directorio del run

        Returns:
            Dict con metadata del run o None si no es válido
        """
        run_id = run_dir.name

        # Buscar archivos principales
        csv_file = run_dir / f"{run_id}.csv"
        jsonl_file = run_dir / f"{run_id}.jsonl"
        metadata_file = run_dir / "metadata.json"
        media_dir = run_dir / "media"

        # Obtener estadísticas
        file_count = len(list(run_dir.glob("*")))
        media_count = 0
        if media_dir.exists():
            media_count = len(list(media_dir.glob("*")))

        # Obtener tamaño total
        total_size = sum(
            f.stat().st_size
            for f in run_dir.rglob("*")
            if f.is_file()
        )

        # Timestamp de creación
        created_at = datetime.fromtimestamp(
            run_dir.stat().st_ctime
        ).isoformat()

        return {
            "run_id": run_id,
            "path": str(run_dir),
            "has_csv": csv_file.exists(),
            "has_jsonl": jsonl_file.exists(),
            "has_metadata": metadata_file.exists(),
            "media_count": media_count,
            "file_count": file_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "created_at": created_at
        }

    def delete_run(self, run_id: str) -> Dict:
        """
        Elimina un run específico del disco.

        Args:
            run_id: ID del run a eliminar

        Returns:
            Dict con resultado de la operación
        """
        run_path = self.base_path / run_id

        if not run_path.exists():
            return {
                "success": False,
                "message": f"Run {run_id} no encontrado"
            }

        try:
            shutil.rmtree(run_path)
            return {
                "success": True,
                "message": f"Run {run_id} eliminado exitosamente"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al eliminar run: {str(e)}"
            }

    def cleanup_old_runs(
        self,
        keep_count: int = 10,
        min_size_mb: Optional[float] = None
    ) -> Dict:
        """
        Limpia runs antiguos manteniendo solo los más recientes.

        Args:
            keep_count: Número de runs a mantener
            min_size_mb: Tamaño mínimo en MB para considerar en limpieza

        Returns:
            Dict con estadísticas de limpieza
        """
        runs = self.list_saved_runs()

        # Filtrar por tamaño si se especifica
        if min_size_mb is not None:
            runs = [r for r in runs if r['total_size_mb'] >= min_size_mb]

        # Runs a eliminar (los que excedan keep_count)
        to_delete = runs[keep_count:]

        deleted_count = 0
        deleted_size = 0
        errors = []

        for run in to_delete:
            result = self.delete_run(run['run_id'])
            if result['success']:
                deleted_count += 1
                deleted_size += run['total_size_mb']
            else:
                errors.append(result['message'])

        return {
            "deleted_count": deleted_count,
            "deleted_size_mb": round(deleted_size, 2),
            "kept_count": min(keep_count, len(runs)),
            "errors": errors
        }
