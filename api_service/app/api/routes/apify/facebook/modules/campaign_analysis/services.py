import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from fastapi import HTTPException

from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

logger = logging.getLogger(__name__)

from .pdf_renderer import EnhancedPDFGenerator

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def analyze_text(self, prompt: str, model: str = "gpt-4o") -> str:
        if not self.client:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        try:
            # Sin límite de tokens - análisis profundo
            response = self.client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "system",
                    "content": "Eres un experto analista de marketing digital. IMPORTANTE: Toda tu respuesta debe ser en ESPAÑOL. Proporciona análisis profundos y detallados."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                response_format={"type": "json_object"}
                # NO max_tokens - sin límite
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise HTTPException(status_code=500, detail=f"OpenAI Analysis failed: {str(e)}")

def map_openai_to_pdf_data(openai_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps the OpenAI JSON output to the structure expected by EnhancedPDFGenerator.
    """
    # 1. Meta Info
    report_meta = openai_data.get('report_meta', {})
    meta_info = {
        "report_title": f"Análisis de Campaña: {report_meta.get('brand_detected', 'Marca Desconocida')}",
        "generated_date": datetime.now().strftime('%Y-%m-%d'),
        "brand_tone_detected": "Profesional / Orientado a Resultados" # Default or extract if available
    }

    # 2. Executive Summary
    exec_summary_in = openai_data.get('executive_summary', {})
    executive_summary = {
        "overview": exec_summary_in.get('performance_overview', 'Sin resumen disponible.'),
        "investment_efficiency_score": 8.5 # Placeholder or calculate based on metrics if available
    }

    # 3. Campaign Stats (Mocked or extracted if available in input)
    campaign_stats_highlight = {
        "total_ads": str(report_meta.get('sample_size', '10')),
        "analysis_focus": report_meta.get('ranking_metric_used', 'N/A')
    }

    # 4. Top Performers
    top_10 = openai_data.get('top_10_analysis', [])
    top_performers = []
    for item in top_10[:3]: # Top 3 for the highlight section
        top_performers.append({
            "ad_id": item.get('ad_id', 'N/A'),
            "analysis_content": f"{item.get('key_takeaway', '')} Hook: {item.get('forensic_breakdown', {}).get('hook_strategy', '')}"
        })

    # 5. Bottom Performers (Not explicitly in top 10, but we can use lower ranked ones if available, or empty)
    bottom_performers = []
    if len(top_10) > 3:
         for item in top_10[-2:]: # Last 2 as "bottom" of the top 10 for contrast, or leave empty
            bottom_performers.append({
                "ad_id": item.get('ad_id', 'N/A'),
                "analysis_content": f"Rank {item.get('rank')}: {item.get('key_takeaway', '')}"
            })

    # 6. Strategic Deep Dive
    # Map recommendations to deep dive keys if possible, or use generic mapping
    strategic_recommendations = openai_data.get('strategic_recommendations', [])
    strategic_deep_dive = {
        "visual_strategy": strategic_recommendations[0] if len(strategic_recommendations) > 0 else "N/A",
        "copywriting_audit": strategic_recommendations[1] if len(strategic_recommendations) > 1 else "N/A",
        "audience_resonance": strategic_recommendations[2] if len(strategic_recommendations) > 2 else "N/A"
    }

    # 7. Actionable Roadmap
    actionable_roadmap = strategic_recommendations # Use the list directly

    return {
        "meta_info": meta_info,
        "executive_summary": executive_summary,
        "campaign_stats_highlight": campaign_stats_highlight,
        "top_performers": top_performers,
        "bottom_performers": bottom_performers,
        "strategic_deep_dive": strategic_deep_dive,
        "actionable_roadmap": actionable_roadmap
    }

def analyze_campaign(run_id: str, run_dir: Path, top_ads: List[Dict], openai_service: OpenAIService) -> Dict[str, Any]:
    """
    Orchestrates the analysis: prepares data, calls OpenAI, saves JSON.
    """
    logger.info(f"Starting analysis for run {run_id}")
    
    # 1. Prepare Data
    ads_summary = json.dumps(top_ads, indent=2)
    
    # 2. Load Prompt (Keeping the same prompt structure as requested)
    system_instruction = """Actúa como un Director de Estrategia de Marketing y Data Scientist Senior, experto en análisis de rendimiento de video, semiótica de marca y psicología del consumidor.

Tu misión es realizar un análisis forense de alto nivel sobre los **10 mejores activos de video** de una campaña, basándote en los archivos de datos (CSV/JSON) y los archivos de medios proporcionados.

Tu objetivo final es retornar **únicamente** un objeto JSON estructurado con tus hallazgos. Este JSON será procesado por un sistema externo (como ReportLab) para generar un informe PDF.

**NO generes texto conversacional, código LaTeX, HTML o Markdown fuera del bloque JSON. Tu única salida debe ser el objeto JSON crudo.**

### FORMATO DE SALIDA REQUERIDO (JSON):
{
  "report_meta": {
    "generated_role": "Senior Data Scientist & Marketing Director",
    "brand_detected": "(Nombre de la marca identificada)",
    "ranking_metric_used": "(Nombre de la métrica usada para ordenar, ej: ROAS)",
    "sample_size": "Top 10 Best Performing Videos"
  },
  "executive_summary": {
    "performance_overview": "(Resumen estratégico de por qué estos 10 videos funcionaron mejor que el resto, basado en los datos)",
    "common_success_patterns": "(Patrones visuales o narrativos recurrentes encontrados en el Top 10)"
  },
  "top_10_analysis": [
    {
      "rank": 1,
      "ad_id": "(ID del video)",
      "metrics": {
        "primary_metric_value": "(Valor real del CSV)",
        "ctr": "(Valor real)",
        "spend": "(Valor real si existe)"
      },
      "forensic_breakdown": {
        "hook_strategy": "(Análisis del gancho visual en los primeros 3 seg)",
        "audio_mood": "(Descripción profesional del audio)",
        "narrative_structure": "(Ej: Problema/Solución, UGC, Testimonial)"
      },
      "expert_scores": {
        "visual_hook": 9,
        "storytelling": 8,
        "brand_integration": 9,
        "conversion_driver": 10
      },
      "key_takeaway": "(Conclusión de una frase sobre este video)"
    }
  ],
  "strategic_recommendations": [
    "(Recomendación 1)",
    "(Recomendación 2)",
    "(Recomendación 3)"
  ]
}
"""
    
    full_prompt = f"{system_instruction}\n\nHere is the data for the top ads:\n{ads_summary}"
    
    # 3. Call OpenAI
    analysis_json_str = openai_service.analyze_text(full_prompt)
    
    try:
        analysis_data = json.loads(analysis_json_str)
    except json.JSONDecodeError:
        logger.error("Failed to decode OpenAI response as JSON")
        raise HTTPException(status_code=500, detail="Invalid JSON response from OpenAI")
        
    # 4. Save JSON
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(exist_ok=True)
    json_path = reports_dir / f"{run_id}_analysis.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
    return {
        "json_data": analysis_data,
        "report_path": str(json_path)
    }

class PDFGenerator:
    def __init__(self, output_path: str):
        self.output_path = output_path

    def generate(self, openai_data: Dict[str, Any]) -> str:
        # Map data to EnhancedPDFGenerator format
        pdf_data = map_openai_to_pdf_data(openai_data)
        
        # Generate PDF
        generator = EnhancedPDFGenerator(self.output_path, pdf_data)
        return generator.render()
