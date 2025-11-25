"""
Facebook Routes - Servicio de Preparación de Datasets
Maneja análisis y preparación de datos scrapeados
"""

from typing import Dict
from pathlib import Path
import json


class PreparationService:
    """
    Servicio para preparar y analizar datasets.
    Encapsula lógica de procesamiento de datos.
    """

    def __init__(self, base_path: Path):
        """
        Inicializa el servicio con ruta base.

        Args:
            base_path: Ruta base donde están los datasets
        """
        self.base_path = base_path

    async def analyze_dataset(
        self,
        run_id: str,
        analysis_type: str = 'basic'
    ) -> Dict:
        """
        Analiza un dataset y genera estadísticas.

        Args:
            run_id: ID del run a analizar
            analysis_type: Tipo de análisis ('basic', 'detailed')

        Returns:
            Dict con resultados del análisis
        """
        from app.processors.facebook.analyze_dataset import (
            analyze,
            analyze_jsonl
        )

        run_path = self.base_path / run_id
        if not run_path.exists():
            return {
                "success": False,
                "message": f"Run {run_id} no encontrado"
            }

        try:
            # Buscar archivo JSONL
            jsonl_file = run_path / f"{run_id}.jsonl"

            if jsonl_file.exists():
                results = analyze_jsonl(str(jsonl_file))
            else:
                # Fallback a CSV si existe
                csv_file = run_path / f"{run_id}.csv"
                if csv_file.exists():
                    results = analyze(str(csv_file))
                else:
                    return {
                        "success": False,
                        "message": "No se encontró archivo de datos"
                    }

            return {
                "success": True,
                "run_id": run_id,
                "analysis": results
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error en análisis: {str(e)}"
            }

    async def prepare_top_n(
        self,
        run_id: str,
        top: int = 10,
        sort_by: str = 'impressions'
    ) -> Dict:
        """
        Prepara los top N anuncios de un dataset.

        Args:
            run_id: ID del run
            top: Número de anuncios top a extraer
            sort_by: Campo para ordenar

        Returns:
            Dict con los top anuncios preparados
        """
        run_path = self.base_path / run_id
        jsonl_file = run_path / f"{run_id}.jsonl"

        if not jsonl_file.exists():
            return {
                "success": False,
                "message": f"Archivo {run_id}.jsonl no encontrado"
            }

        try:
            # Leer y parsear JSONL
            ads = []
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        ads.append(json.loads(line))

            # Ordenar por el campo especificado
            sorted_ads = sorted(
                ads,
                key=lambda x: x.get(sort_by, 0),
                reverse=True
            )

            # Tomar top N
            top_ads = sorted_ads[:top]

            # Guardar resultado preparado
            output_path = run_path / f"{run_id}_top{top}_prepared.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(top_ads, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "run_id": run_id,
                "top_count": len(top_ads),
                "output_file": str(output_path),
                "data": top_ads
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error preparando top {top}: {str(e)}"
            }
