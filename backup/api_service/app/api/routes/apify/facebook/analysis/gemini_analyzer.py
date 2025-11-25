"""
Gemini Analyzer Module
Analiza campañas usando Google Gemini AI
"""
import json
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException


def analyze_campaign_with_gemini(
    run_id: str,
    manifest_data: Dict[str, Any],
    analysis_prompt: str,
    gemini_service: Any,
    reports_dir: Path,
    source: str = "url"
) -> Dict[str, Any]:
    """
    Analiza una campaña usando Gemini AI

    Args:
        run_id: ID del run
        manifest_data: Manifest con ads y archivos
        analysis_prompt: Prompt para el análisis
        gemini_service: Instancia de GeminiService
        reports_dir: Directorio donde guardar reportes
        source: Origen del análisis ("url" o "gcs_bucket")

    Returns:
        Dict con análisis completo en formato JSON

    Raises:
        HTTPException: Si hay error en análisis o parsing
    """
    # Construir prompt completo
    full_prompt = f"""
{analysis_prompt}

CAMPAÑA ID: {run_id}
TOTAL DE ANUNCIOS: {len(manifest_data.get('ads', []))}

ANUNCIOS A ANALIZAR:
"""

    for idx, ad in enumerate(manifest_data.get('ads', []), 1):
        ad_id = ad.get('ad_id', 'N/A')
        files = ad.get('files', [])

        full_prompt += f"\n--- ANUNCIO #{idx} (ID: {ad_id}) ---\n"
        full_prompt += f"Archivos multimedia: {len(files)}\n"

        for file_info in files:
            file_url = file_info.get('url', 'N/A')
            file_type = file_info.get('type', 'unknown')
            full_prompt += f"  - Tipo: {file_type}, URL: {file_url}\n"

    full_prompt += """

GENERA UN ANÁLISIS COMPLETO EN FORMATO JSON CON:
1. campaign_summary: resumen general y mejor anuncio
2. ads_analysis: análisis detallado por anuncio con scores
3. comparative_analysis: por qué ganó el mejor
4. recommendations: mejores prácticas identificadas
5. latex_code: código LaTeX completo para generar PDF del reporte

El latex_code debe incluir:
- Documento LaTeX completo compilable
- Tablas con scores
- Listas con fortalezas/debilidades
- Secciones de recomendaciones
- Formato profesional

Responde SOLO con JSON válido.
"""

    # Analizar con Gemini
    try:
        gemini_result = gemini_service.generate_text(
            prompt=full_prompt,
            temperature=0.4,
            max_tokens=8000
        )

        if gemini_result['status'] == 'error':
            raise HTTPException(
                status_code=500,
                detail=f"Gemini error: {gemini_result.get('error')}"
            )

        response_text = gemini_result.get('response', '')

        # Extract JSON
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to parse Gemini response as JSON"
            )

        analysis_json = json.loads(
            response_text[json_start:json_end]
        )

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON from Gemini: {str(e)}"
        )

    return analysis_json


def save_analysis_results(
    run_id: str,
    analysis_json: Dict[str, Any],
    reports_dir: Path,
    source: str = "url"
) -> Dict[str, Any]:
    """
    Guarda los resultados del análisis en archivos

    Args:
        run_id: ID del run
        analysis_json: JSON con el análisis completo
        reports_dir: Directorio donde guardar
        source: Origen ("url" o "gcs_bucket")

    Returns:
        Dict con paths de archivos guardados
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = "_from_bucket" if source == "gcs_bucket" else ""

    # Guardar JSON
    report_filename = f'{run_id}_analysis{suffix}_{timestamp}.json'
    report_path = reports_dir / report_filename

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_json, f, indent=2, ensure_ascii=False)

    # Guardar LaTeX si existe
    latex_code = analysis_json.get('latex_code')
    latex_filename = None
    latex_path = None

    if latex_code:
        latex_filename = f'{run_id}_report{suffix}_{timestamp}.tex'
        latex_path = reports_dir / latex_filename

        with open(latex_path, 'w', encoding='utf-8') as f:
            f.write(latex_code)

    return {
        'report_path': report_path,
        'report_filename': report_filename,
        'latex_path': latex_path,
        'latex_filename': latex_filename
    }
