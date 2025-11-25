from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from ...routes.scraper import scrape_and_save
from ...models.schemas import SimpleScrapeRequest
from ...utils.config import get_facebook_saved_base
from .services import OpenAIService, PDFGenerator, analyze_campaign

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze-url", status_code=200)
async def analyze_url(request: SimpleScrapeRequest):
    """
    Endpoint integrado para análisis de campañas:
    1. Scrapea URL de Meta Ads.
    2. Analiza con OpenAI (Top 10 videos).
    3. Genera reporte PDF.
    """
    try:
        logger.info(f"🚀 Iniciando análisis de campaña para URL: {request.url}")
        
        # 1. Scrape & Save (Reusing existing logic)
        scrape_result = await scrape_and_save(request)
        run_id = scrape_result['run_id']
        top_ads = scrape_result.get('top_ads', [])
        
        if not top_ads:
            logger.warning(f"No top ads found for run {run_id}")
            
        base = get_facebook_saved_base()
        run_dir = base / run_id
        
        # 2. OpenAI Analysis
        openai_service = OpenAIService()
        analysis_result = analyze_campaign(run_id, run_dir, top_ads, openai_service)
        
        # 3. PDF Generation
        json_data = analysis_result['json_data']
        pdf_path = run_dir / f"Reporte_Analisis_{run_id}.pdf"
        
        pdf_generator = PDFGenerator(str(pdf_path))
        final_pdf_path = pdf_generator.generate(json_data)
        
        return {
            "status": "success",
            "run_id": run_id,
            "pdf_path": str(final_pdf_path),
            "json_report": analysis_result['report_path'],
            "scrape_stats": scrape_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze-url: {e}")
        raise HTTPException(status_code=500, detail=str(e))
