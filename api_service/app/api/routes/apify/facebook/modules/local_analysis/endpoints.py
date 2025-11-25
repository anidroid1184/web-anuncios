from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Dict, Any
import logging
from pathlib import Path
import json
import os
import base64
from io import BytesIO
from PIL import Image
import pandas as pd
import re

from ...utils.config import get_facebook_saved_base
from ...models.schemas import SimpleScrapeRequest
from ..campaign_analysis.services import PDFGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze-local-and-pdf", status_code=200)
async def analyze_local_and_pdf(run_id: str = Query(..., description="ID del run de Apify con los datos locales")):
    """
    Endpoint para análisis local completo con generación automática de PDF.
    
    Basado en el funcionamiento de /analyze-local-only (usa Base64).
    
    Este endpoint:
    1. Carga TODOS los anuncios del CSV
    2. Extrae frames de videos locales
    3. Convierte imágenes y frames a Base64
    4. Envía TODO a OpenAI (sin límite de tokens)
    5. Genera PDF profesional automáticamente
    
    Args:
        run_id: ID del run con datos locales guardados
        
    Returns:
        JSON con paths al PDF y reporte JSON generados
    """
    try:
        logger.info("="*80)
        logger.info(f"🚀 ANÁLISIS LOCAL COMPLETO CON PDF - RUN: {run_id}")
        logger.info("="*80)
        
        # PASO 1: Configurar OpenAI
        logger.info("\n📡 PASO 1: Configurando OpenAI...")
        from openai import AsyncOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
        if not api_key:
            raise HTTPException(503, "OPENAI_API_KEY no configurada")
        
        openai_client = AsyncOpenAI(api_key=api_key)
        logger.info("   ✅ OpenAI configurado")
        
        # PASO 2: Localizar CSV
        logger.info("\n📊 PASO 2: Localizando dataset...")
        base_dir = get_facebook_saved_base()
        run_dir = base_dir / run_id
        csv_path = run_dir / f"{run_id}.csv"
        
        if not csv_path.exists():
            raise HTTPException(404, f"CSV no encontrado en {csv_path}")
        
        logger.info(f"   ✅ CSV: {csv_path}")
        
        # PASO 3: Cargar TODOS los anuncios
        logger.info("\n📊 PASO 3: Cargando TODOS los anuncios...")
        df = pd.read_csv(csv_path)
        logger.info(f"   📄 CSV cargado: {len(df)} anuncios totales")
        
        # PASO 4: Buscar archivos multimedia locales
        logger.info("\n📦 PASO 4: Buscando archivos multimedia...")
        media_dir = run_dir / "media"
        video_frames_dir = run_dir / "video_frames"
        
        if not media_dir.exists():
            raise HTTPException(404, f"Directorio media no existe: {media_dir}")
        
        logger.info(f"   📁 Media: {media_dir}")
        
        # PASO 4.1: Extraer frames de videos
        logger.info("\n🎬 Extrayendo frames de videos...")
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        video_files = [
            f for f in media_dir.iterdir()
            if f.is_file() and f.suffix.lower() in video_extensions
        ]
        
        if video_files:
            logger.info(f"   📹 {len(video_files)} videos encontrados")
            video_frames_dir.mkdir(exist_ok=True)
            
            try:
                import cv2
                for video_path in video_files:
                    try:
                        logger.info(f"   🔄 Procesando: {video_path.name}")
                        cap = cv2.VideoCapture(str(video_path))
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        
                        frames_to_extract = [0, frame_count // 2, frame_count - 1]
                        base_name = video_path.stem
                        extracted = 0
                        
                        for i, frame_num in enumerate(frames_to_extract):
                            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                            ret, frame = cap.read()
                            if ret:
                                frame_filename = f"{base_name}_frame{i}.jpg"
                                frame_path = video_frames_dir / frame_filename
                                cv2.imwrite(str(frame_path), frame)
                                extracted += 1
                        
                        cap.release()
                        logger.info(f"      ✅ {extracted} frames extraídos")
                    except Exception as e:
                        logger.error(f"      ❌ Error con {video_path.name}: {e}")
            except ImportError:
                logger.warning("   ⚠️  OpenCV no disponible")
        
        has_video_frames = video_frames_dir.exists()
        
        # PASO 5: Cargar prompt desde .env o archivo
        logger.info("\n📄 PASO 5: Cargando prompt...")
        
        # Primero intentar desde variable de entorno
        prompt_template = os.getenv('PROMPT')
        
        if prompt_template:
            logger.info(f"   ✅ Prompt cargado desde variable PROMPT del .env ({len(prompt_template)} caracteres)")
        else:
            # Si no está en .env, buscar archivo
            prompt_file_name = os.getenv('PROMPT_FILE', 'prompt.txt')
            api_service_dir = Path(__file__).parent.parent.parent.parent.parent.parent.parent
            prompt_path = api_service_dir / prompt_file_name
            
            logger.info(f"   🔍 Buscando prompt en: {prompt_path}")
            
            if prompt_path.exists():
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_template = f.read().strip()
                logger.info(f"   ✅ Prompt cargado desde {prompt_file_name} ({len(prompt_template)} caracteres)")
            else:
                # Fallback a DEFAULT_PROMPT
                try:
                    from app.api.routes.apify.facebook.analysis.prompts import DEFAULT_PROMPT
                    prompt_template = DEFAULT_PROMPT
                    logger.warning(f"   ⚠️  Archivo {prompt_file_name} no encontrado, usando DEFAULT_PROMPT")
                except ImportError:
                    prompt_template = "Analiza estos anuncios de Facebook de manera PROFUNDA y DETALLADA. TODO en ESPAÑOL."
                    logger.warning("   ⚠️  Usando prompt por defecto básico")
        
        # PASO 6: Preparar contenido para OpenAI con Base64
        logger.info("\n🖼️  PASO 6: Preparando imágenes en Base64...")
        
        # Límite fijo de imágenes
        MAX_IMAGES = 50
        max_static_images = int(MAX_IMAGES * 0.6)  # 60% = 30 imágenes
        max_video_frames = int(MAX_IMAGES * 0.4)   # 40% = 20 frames
        
        logger.info(f"   ⚙️  Límite total: {MAX_IMAGES}")
        logger.info(f"   📊 Proporción: {max_static_images} imágenes + {max_video_frames} frames de video")
        
        dataset_info = f"""
INFORMACIÓN DEL DATASET:
- Run ID: {run_id}
- Total de anuncios: {len(df)}
- Imágenes estáticas: {max_static_images}
- Frames de video: {max_video_frames}
- Total multimedia: {MAX_IMAGES}

INSTRUCCIÓN CRÍTICA: 
- Debes retornar ÚNICAMENTE un objeto JSON válido y completo
- TODO en ESPAÑOL
- Análisis PROFUNDO y DETALLADO
- Contrasta imágenes estáticas con frames de video
- No agregues texto adicional antes o después del JSON

### FORMATO DE SALIDA REQUERIDO (JSON):
{{
  "report_meta": {{
    "generated_role": "Senior Data Scientist & Marketing Director",
    "brand_detected": "(Nombre de la marca identificada en los anuncios)",
    "ranking_metric_used": "(Métrica principal analizada)",
    "sample_size": "{len(df)} anuncios analizados"
  }},
  "executive_summary": {{
    "performance_overview": "(Resumen estratégico PROFUNDO y DETALLADO de los hallazgos principales. Mínimo 200 palabras explicando patrones, tendencias y conclusiones clave)",
    "common_success_patterns": "(Patrones visuales, narrativos o estratégicos recurrentes encontrados)"
  }},
  "top_10_analysis": [
    {{
      "rank": 1,
      "ad_id": "(ID o identificador del anuncio)",
      "metrics": {{
        "primary_metric_value": "(Valor principal si está disponible)",
        "ctr": "(CTR si está disponible)",
        "spend": "(Gasto si está disponible)"
      }},
      "forensic_breakdown": {{
        "hook_strategy": "(Análisis DETALLADO del gancho visual en los primeros 3 segundos)",
        "audio_mood": "(Descripción profesional del audio y su impacto)",
        "narrative_structure": "(Estructura narrativa: Problema/Solución, UGC, Testimonial, etc.)"
      }},
      "expert_scores": {{
        "visual_hook": 9,
        "storytelling": 8,
        "brand_integration": 9,
        "conversion_driver": 10
      }},
      "key_takeaway": "(Conclusión DETALLADA de una o dos frases sobre este anuncio)"
    }}
  ],
  "strategic_recommendations": [
    "(Recomendación estratégica 1 - DETALLADA y ACCIONABLE)",
    "(Recomendación estratégica 2 - DETALLADA y ACCIONABLE)",
    "(Recomendación estratégica 3 - DETALLADA y ACCIONABLE)"
  ]
}}

IMPORTANTE: 
- El campo "performance_overview" debe ser EXTENSIVO y DETALLADO (mínimo 200 palabras)
- Analiza TODOS los anuncios proporcionados, no solo los top 10
- Proporciona insights profundos basados en las imágenes y frames de video analizados
- Las recomendaciones deben ser específicas y accionables
"""
        
        content_blocks = []
        content_blocks.append({
            "type": "text",
            "text": dataset_info + "\n\n" + prompt_template
        })
        
        total_imgs = 0
        total_video_frames = 0
        
        # PRIMERO: Procesar frames de video (40%)
        if has_video_frames:
            logger.info(f"\n   📹 PASO 6.1: Procesando hasta {max_video_frames} frames de video...")
            video_frame_files = [f for f in video_frames_dir.iterdir() 
                                if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
            
            for frame_file in video_frame_files:
                if total_video_frames >= max_video_frames:
                    logger.info(f"   ⚠️  Límite de {max_video_frames} frames alcanzado")
                    break
                    
                try:
                    with Image.open(frame_file) as img:
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGB')
                        if max(img.size) > 800:
                            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                        
                        buffered = BytesIO()
                        img.save(buffered, format="JPEG", quality=85, optimize=True)
                        b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        
                        content_blocks.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "high"
                            }
                        })
                        total_video_frames += 1
                        if total_video_frames % 5 == 0:
                            logger.info(f"   ✓ Procesados {total_video_frames} frames...")
                except Exception as e:
                    logger.error(f"   ✗ Error en {frame_file.name}: {e}")
            
            logger.info(f"   ✅ Total frames de video: {total_video_frames}")
        
        # SEGUNDO: Procesar imágenes estáticas (60%)
        logger.info(f"\n   🖼️  PASO 6.2: Procesando hasta {max_static_images} imágenes estáticas...")
        image_files = [f for f in media_dir.iterdir() 
                      if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']]
        
        for img_file in image_files:
            if total_imgs >= max_static_images:
                logger.info(f"   ⚠️  Límite de {max_static_images} imágenes alcanzado")
                break
                
            try:
                with Image.open(img_file) as img:
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    if max(img.size) > 800:
                        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                    
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG", quality=85, optimize=True)
                    b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    content_blocks.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                            "detail": "high"
                        }
                    })
                    total_imgs += 1
                    if total_imgs % 10 == 0:
                        logger.info(f"   ✓ Procesadas {total_imgs} imágenes...")
            except Exception as e:
                logger.error(f"   ✗ Error en {img_file.name}: {e}")
        
        logger.info(f"   ✅ Total imágenes estáticas: {total_imgs}")
        
        # PASO 7: Enviar a OpenAI (SIN LÍMITE DE TOKENS)
        logger.info("\n🤖 PASO 7: Enviando a OpenAI...")
        logger.info(f"   📊 Total: {total_imgs} imágenes + {total_video_frames} frames de video")
        
        total_assets = total_imgs + total_video_frames
        if total_assets == 0:
            raise HTTPException(400, "No se procesó ninguna multimedia")
        
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto analista de marketing digital y publicidad. IMPORTANTE: Toda tu respuesta debe ser en ESPAÑOL. Debes analizar anuncios publicitarios de manera profesional y proporcionar análisis profundos y detallados. Retorna ÚNICAMENTE un objeto JSON válido."
                },
                {"role": "user", "content": content_blocks}
            ],
            response_format={"type": "json_object"}
            # Sin límite de max_tokens para permitir respuesta completa
        )
        
        analysis = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        logger.info(f"   ✅ Completado - {tokens_used} tokens usados")
        logger.info(f"   📝 Longitud de respuesta: {len(analysis) if analysis else 0} caracteres")
        logger.info(f"   📝 Tipo de respuesta: {type(analysis)}")
        logger.info(f"   📝 Primeros 200 caracteres: {analysis[:200] if analysis else 'VACÍO'}")
        
        # PASO 8: Guardar JSON
        logger.info("\n💾 PASO 8: Guardando análisis...")
        reports_dir = run_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        # Verificar que la respuesta no esté vacía o rechazada
        if not analysis or analysis.strip() == "":
            logger.error("   ❌ OpenAI devolvió una respuesta VACÍA")
            raise HTTPException(
                status_code=500,
                detail="OpenAI returned empty response. This may be due to content filtering or API issues."
            )
        
        # Verificar si OpenAI rechazó la solicitud
        if "no puedo ayudar" in analysis.lower() or "sorry" in analysis.lower() or "cannot" in analysis.lower():
            logger.error(f"   ❌ OpenAI rechazó la solicitud: {analysis[:200]}")
            raw_path = reports_dir / f"{run_id}_raw_response.txt"
            with open(raw_path, 'w', encoding='utf-8') as f:
                f.write(analysis)
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI rechazó la solicitud. Esto puede deberse a filtros de contenido. Respuesta guardada en {raw_path}"
            )
        
        # Intentar parsear JSON
        analysis_data = None
        try:
            analysis_data = json.loads(analysis)
            logger.info("   ✅ JSON parseado correctamente")
        except json.JSONDecodeError as e:
            logger.warning(f"   ⚠️  Error parseando JSON: {e}")
            logger.info("   🔧 Intentando reparar JSON...")
            
            # Guardar respuesta raw ANTES de intentar reparar
            raw_path = reports_dir / f"{run_id}_raw_response.txt"
            with open(raw_path, 'w', encoding='utf-8') as f:
                f.write(analysis)
            logger.info(f"   💾 Respuesta raw guardada en: {raw_path}")
            
            try:
                from json_repair import loads as repair_loads
                # loads() repara Y parsea en un solo paso, devuelve dict
                repaired = repair_loads(analysis)
                # Asegurar que sea un dict, no un string
                if isinstance(repaired, str):
                    analysis_data = json.loads(repaired)
                elif isinstance(repaired, dict):
                    analysis_data = repaired
                else:
                    raise ValueError(f"json_repair devolvió un tipo inesperado: {type(repaired)}")
                logger.info(f"   ✅ JSON reparado exitosamente - Tipo: {type(analysis_data)}")
            except Exception as repair_error:
                logger.error(f"   ❌ No se pudo reparar JSON: {repair_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"OpenAI no devolvió JSON válido. Respuesta guardada en {raw_path}"
                )
        
        # Verificar que sea un dict
        if not isinstance(analysis_data, dict):
            logger.error(f"   ❌ analysis_data no es un dict, es: {type(analysis_data)}")
            logger.error(f"   📝 Contenido: {str(analysis_data)[:500]}")
            raw_path = reports_dir / f"{run_id}_raw_response.txt"
            with open(raw_path, 'w', encoding='utf-8') as f:
                f.write(analysis)
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI response is not a valid JSON object, got {type(analysis_data)}. Respuesta guardada en {raw_path}"
            )
        
        json_path = reports_dir / f"{run_id}_analysis_complete.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"   ✅ JSON guardado: {json_path}")
        
        # PASO 9: Generar PDF
        logger.info("\n📄 PASO 9: Generando PDF profesional...")
        pdf_path = reports_dir / f"Reporte_Analisis_Completo_{run_id}.pdf"
        
        pdf_generator = PDFGenerator(str(pdf_path))
        final_pdf_path = pdf_generator.generate(analysis_data)
        
        logger.info(f"   ✅ PDF generado: {final_pdf_path}")
        logger.info("="*80)
        logger.info("✅ ANÁLISIS COMPLETO FINALIZADO")
        logger.info("="*80)
        
        return {
            "status": "success",
            "run_id": run_id,
            "pdf_path": str(final_pdf_path),
            "json_report": str(json_path),
            "total_ads_in_csv": len(df),
            "total_images_processed": total_imgs,
            "total_video_frames_processed": total_video_frames,
            "tokens_used": tokens_used,
            "message": "Análisis completo de TODOS los anuncios finalizado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in analyze-local-and-pdf: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-url-with-download", status_code=200)
async def analyze_url_with_download(request: SimpleScrapeRequest):
    """
    Endpoint para analizar una URL que descarga el dataset si no existe localmente.
    
    Este endpoint:
    1. Verifica si el run_id ya existe localmente
    2. Si no existe, hace scraping y descarga el dataset
    3. Si existe, verifica que tenga los archivos necesarios
    4. Si faltan archivos, descarga el dataset desde Apify
    5. Procede con el análisis local y generación de PDF
    
    Args:
        request: SimpleScrapeRequest con url, count, timeout
        
    Returns:
        JSON con paths al PDF y reporte JSON generados
    """
    try:
        from ...routes.scraper import scrape_and_save
        import asyncio
        
        logger.info("="*80)
        logger.info(f"🚀 ANÁLISIS URL CON DESCARGA AUTOMÁTICA - URL: {request.url}")
        logger.info("="*80)
        
        # PASO 1: Hacer scraping para obtener run_id
        logger.info("\n📡 PASO 1: Iniciando scraping...")
        scrape_result = await scrape_and_save(request)
        run_id = scrape_result['run_id']
        logger.info(f"   ✅ Run ID obtenido: {run_id}")
        
        # PASO 2: Verificar si el dataset existe localmente
        logger.info("\n📊 PASO 2: Verificando dataset local...")
        base_dir = get_facebook_saved_base()
        run_dir = base_dir / run_id
        csv_path = run_dir / f"{run_id}.csv"
        jsonl_path = run_dir / f"{run_id}.jsonl"
        media_dir = run_dir / "media"
        
        dataset_exists = csv_path.exists() or jsonl_path.exists()
        media_exists = media_dir.exists() and any(media_dir.iterdir())
        
        logger.info(f"   📁 CSV existe: {csv_path.exists()}")
        logger.info(f"   📁 JSONL existe: {jsonl_path.exists()}")
        logger.info(f"   📁 Media existe: {media_exists}")
        
        # PASO 3: Si no existe el dataset o faltan archivos, descargarlo
        if not dataset_exists or not media_exists:
            logger.info("\n💾 PASO 3: Descargando dataset desde Apify...")
            
            from app.processors.facebook.extract_dataset import fetch_and_store_run_dataset
            
            try:
                # Descargar dataset con media
                dataset_meta = await asyncio.to_thread(
                    fetch_and_store_run_dataset,
                    run_id,
                    out_base=None,  # usa directorio por defecto
                    download_media=True,
                    download_limit=None
                )
                
                logger.info(f"   ✅ Dataset descargado: {dataset_meta.get('items_count', 0)} items")
                if dataset_meta.get('media_saved_count'):
                    logger.info(f"   ✅ Media descargado: {dataset_meta.get('media_saved_count')} archivos")
            except Exception as e:
                logger.warning(f"   ⚠️  Error descargando dataset: {e}")
                logger.info("   ℹ️  Continuando con datos existentes...")
        else:
            logger.info("\n✅ PASO 3: Dataset ya existe localmente, omitiendo descarga")
        
        # PASO 4: Verificar que ahora sí existan los archivos necesarios
        csv_path = run_dir / f"{run_id}.csv"
        if not csv_path.exists():
            raise HTTPException(404, f"CSV no encontrado después de descarga en {csv_path}")
        
        # PASO 5: Detectar y extraer frames de videos (DETECCIÓN ROBUSTA)
        logger.info("\n🎬 PASO 5: Detectando y extrayendo frames de videos...")
        video_frames_dir = run_dir / "video_frames"
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.flv', '.wmv']
        
        # Función para detectar si un archivo es realmente un video
        def is_valid_video_file(file_path: Path) -> bool:
            """Verifica si un archivo es un video válido."""
            # Verificar por extensión
            if file_path.suffix.lower() not in video_extensions:
                return False
            
            # Verificar que el archivo exista y tenga contenido
            if not file_path.exists() or file_path.stat().st_size == 0:
                return False
            
            # Intentar abrir con OpenCV para validar
            try:
                import cv2
                cap = cv2.VideoCapture(str(file_path))
                if cap.isOpened():
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    cap.release()
                    # Un video válido debe tener al menos 1 frame y FPS > 0
                    if frame_count > 0 and fps > 0:
                        return True
            except Exception:
                pass
            
            return False
        
        # Verificar si ya existen frames extraídos
        has_video_frames = False
        existing_frames = []
        if video_frames_dir.exists():
            existing_frames = [
                f for f in video_frames_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']
            ]
            if existing_frames:
                logger.info(f"   ✅ {len(existing_frames)} frames de video ya existen en el directorio")
                has_video_frames = True
        
        # Si no hay frames suficientes, buscar videos y extraerlos
        if not has_video_frames or len(existing_frames) < 10:  # Extraer más si hay pocos frames
            logger.info(f"   🔍 Buscando archivos de video en {media_dir}...")
            
            # Listar todos los archivos en media_dir
            all_files = [f for f in media_dir.iterdir() if f.is_file()]
            logger.info(f"   📁 Total archivos en media/: {len(all_files)}")
            
            # Intentar detectar videos de múltiples formas
            potential_videos = []
            for file_path in all_files:
                # Verificar por extensión
                if file_path.suffix.lower() in video_extensions:
                    potential_videos.append(file_path)
                    logger.info(f"      📹 Detectado por extensión: {file_path.name}")
            
            # Si no encontramos por extensión, buscar por tamaño (videos suelen ser más grandes)
            if not potential_videos:
                logger.info(f"   🔍 No se encontraron videos por extensión, buscando por tamaño...")
                # Archivos > 100KB que no sean imágenes conocidas
                image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
                large_files = [
                    f for f in all_files 
                    if f.suffix.lower() not in image_extensions 
                    and f.stat().st_size > 100 * 1024  # > 100KB
                ]
                logger.info(f"   📊 Archivos grandes encontrados (>100KB): {len(large_files)}")
                potential_videos = large_files[:10]  # Limitar para no procesar demasiados
            
            # Validar cada video potencial
            valid_video_files = []
            for video_path in potential_videos:
                if is_valid_video_file(video_path):
                    valid_video_files.append(video_path)
                    logger.info(f"   ✅ Video válido confirmado: {video_path.name}")
                else:
                    logger.debug(f"   ⚠️  {video_path.name} no es un video válido")
            
            if valid_video_files:
                logger.info(f"   📹 {len(valid_video_files)} videos válidos encontrados, extrayendo frames...")
                video_frames_dir.mkdir(exist_ok=True, parents=True)
                
                try:
                    import cv2
                    frames_extracted = 0
                    max_frames_per_video = max(1, max_video_frames // max(1, len(valid_video_files)))
                    
                    for video_path in valid_video_files:
                        if frames_extracted >= max_video_frames:
                            break
                            
                        try:
                            cap = cv2.VideoCapture(str(video_path))
                            if not cap.isOpened():
                                logger.warning(f"      ⚠️  No se pudo abrir {video_path.name}")
                                continue
                                
                            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                            fps = cap.get(cv2.CAP_PROP_FPS)
                            
                            if frame_count == 0 or fps == 0:
                                logger.warning(f"      ⚠️  Video {video_path.name} inválido (frames: {frame_count}, fps: {fps})")
                                cap.release()
                                continue
                            
                            # Extraer múltiples frames distribuidos a lo largo del video
                            # Para cumplir con el 40% (20 frames de ~50 totales)
                            num_frames_to_extract = min(max_frames_per_video, max_video_frames - frames_extracted)
                            
                            if num_frames_to_extract > 0:
                                # Distribuir frames equitativamente
                                frame_indices = []
                                if num_frames_to_extract == 1:
                                    frame_indices = [frame_count // 2]
                                else:
                                    step = frame_count / (num_frames_to_extract + 1)
                                    frame_indices = [int(i * step) for i in range(1, num_frames_to_extract + 1)]
                                
                                base_name = video_path.stem
                                
                                for idx, frame_num in enumerate(frame_indices):
                                    if frames_extracted >= max_video_frames:
                                        break
                                    
                                    cap.set(cv2.CAP_PROP_POS_FRAMES, min(frame_num, frame_count - 1))
                                    ret, frame = cap.read()
                                    if ret and frame is not None:
                                        frame_filename = f"{base_name}_frame{idx:03d}.jpg"
                                        frame_path = video_frames_dir / frame_filename
                                        
                                        # Redimensionar frame si es muy grande
                                        h, w = frame.shape[:2]
                                        if max(h, w) > 1920:
                                            scale = 1920 / max(h, w)
                                            new_w, new_h = int(w * scale), int(h * scale)
                                            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
                                        
                                        cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                                        frames_extracted += 1
                                        
                                logger.info(f"      ✅ {video_path.name}: {num_frames_to_extract} frames extraídos")
                            
                            cap.release()
                        except Exception as e:
                            logger.error(f"      ❌ Error procesando {video_path.name}: {e}")
                            import traceback
                            logger.debug(traceback.format_exc())
                    
                    # Verificar frames extraídos
                    if video_frames_dir.exists():
                        existing_frames = [
                            f for f in video_frames_dir.iterdir() 
                            if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']
                        ]
                        has_video_frames = len(existing_frames) > 0
                        if has_video_frames:
                            logger.info(f"   ✅ Total: {len(existing_frames)} frames de video extraídos exitosamente")
                        else:
                            logger.warning(f"   ⚠️  No se pudieron extraer frames de video (directorio vacío)")
                    else:
                        logger.warning(f"   ⚠️  No se creó el directorio de frames")
                        
                except ImportError:
                    logger.error("   ❌ OpenCV no disponible. Instala opencv-python: pip install opencv-python")
                except Exception as e:
                    logger.error(f"   ❌ Error durante extracción de frames: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning(f"   ⚠️  No se encontraron videos válidos en el dataset")
                logger.info(f"   💡 Los anuncios pueden ser solo imágenes estáticas")
        
        # PASO 6: Preparar contenido para OpenAI con Base64
        logger.info("\n🖼️  PASO 6: Preparando imágenes en Base64...")
        
        from openai import AsyncOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
        if not api_key:
            raise HTTPException(503, "OPENAI_API_KEY no configurada")
        
        openai_client = AsyncOpenAI(api_key=api_key)
        
        # Cargar CSV
        df = pd.read_csv(csv_path)
        logger.info(f"   📄 CSV cargado: {len(df)} anuncios totales")
        
        MAX_IMAGES = 50
        max_static_images = int(MAX_IMAGES * 0.6)  # 60% = 30 imágenes
        max_video_frames = int(MAX_IMAGES * 0.4)   # 40% = 20 frames
        
        logger.info(f"   ⚙️  Límite total: {MAX_IMAGES}")
        logger.info(f"   📊 Proporción: {max_static_images} imágenes + {max_video_frames} frames de video")
        
        # Cargar prompt desde .env o archivo (igual que el otro endpoint)
        prompt_template = os.getenv('PROMPT')
        
        if not prompt_template:
            prompt_file_name = os.getenv('PROMPT_FILE', 'prompt.txt')
            api_service_dir = Path(__file__).parent.parent.parent.parent.parent.parent.parent
            prompt_path = api_service_dir / prompt_file_name
            
            if prompt_path.exists():
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_template = f.read().strip()
                logger.info(f"   ✅ Prompt cargado desde {prompt_file_name}")
            else:
                try:
                    from app.api.routes.apify.facebook.analysis.prompts import DEFAULT_PROMPT
                    prompt_template = DEFAULT_PROMPT
                except ImportError:
                    prompt_template = "Analiza estos anuncios de Facebook de manera PROFUNDA y DETALLADA. TODO en ESPAÑOL."
        else:
            logger.info(f"   ✅ Prompt cargado desde variable PROMPT del .env")
        
        dataset_info = f"""
INFORMACIÓN DEL DATASET:
- Run ID: {run_id}
- Total de anuncios: {len(df)}
- Imágenes estáticas: {max_static_images}
- Frames de video: {max_video_frames}
- Total multimedia: {MAX_IMAGES}

INSTRUCCIÓN CRÍTICA: 
- Debes retornar ÚNICAMENTE un objeto JSON válido y completo
- TODO en ESPAÑOL
- Análisis PROFUNDO y DETALLADO
- Contrasta imágenes estáticas con frames de video
- No agregues texto adicional antes o después del JSON

### FORMATO DE SALIDA REQUERIDO (JSON):
{{
  "report_meta": {{
    "generated_role": "Senior Data Scientist & Marketing Director",
    "brand_detected": "(Nombre de la marca identificada en los anuncios)",
    "ranking_metric_used": "(Métrica principal analizada)",
    "sample_size": "{len(df)} anuncios analizados"
  }},
  "executive_summary": {{
    "performance_overview": "(Resumen estratégico PROFUNDO y DETALLADO de los hallazgos principales. Mínimo 200 palabras explicando patrones, tendencias y conclusiones clave)",
    "common_success_patterns": "(Patrones visuales, narrativos o estratégicos recurrentes encontrados)"
  }},
  "top_10_analysis": [
    {{
      "rank": 1,
      "ad_id": "(ID o identificador del anuncio)",
      "metrics": {{
        "primary_metric_value": "(Valor principal si está disponible)",
        "ctr": "(CTR si está disponible)",
        "spend": "(Gasto si está disponible)"
      }},
      "forensic_breakdown": {{
        "hook_strategy": "(Análisis DETALLADO del gancho visual en los primeros 3 segundos)",
        "audio_mood": "(Descripción profesional del audio y su impacto)",
        "narrative_structure": "(Estructura narrativa: Problema/Solución, UGC, Testimonial, etc.)"
      }},
      "expert_scores": {{
        "visual_hook": 9,
        "storytelling": 8,
        "brand_integration": 9,
        "conversion_driver": 10
      }},
      "key_takeaway": "(Conclusión DETALLADA de una o dos frases sobre este anuncio)"
    }}
  ],
  "strategic_recommendations": [
    "(Recomendación estratégica 1 - DETALLADA y ACCIONABLE)",
    "(Recomendación estratégica 2 - DETALLADA y ACCIONABLE)",
    "(Recomendación estratégica 3 - DETALLADA y ACCIONABLE)"
  ]
}}

IMPORTANTE: 
- El campo "performance_overview" debe ser EXTENSIVO y DETALLADO (mínimo 200 palabras)
- Analiza TODOS los anuncios proporcionados, no solo los top 10
- Proporciona insights profundos basados en las imágenes y frames de video analizados
- Las recomendaciones deben ser específicas y accionables
"""
        
        content_blocks = []
        content_blocks.append({
            "type": "text",
            "text": dataset_info + "\n\n" + prompt_template
        })
        
        total_imgs = 0
        total_video_frames = 0
        
        # PRIMERO: Procesar frames de video (40%) - PRIORITARIO si están disponibles
        if has_video_frames and video_frames_dir.exists():
            logger.info(f"\n   📹 PASO 6.1: Procesando hasta {max_video_frames} frames de video (40% del total)...")
            video_frame_files = sorted([
                f for f in video_frames_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']
            ], key=lambda x: x.stat().st_mtime)  # Ordenar por fecha de modificación
            
            logger.info(f"   📊 {len(video_frame_files)} frames disponibles para procesar")
            
            if not video_frame_files:
                logger.warning(f"   ⚠️  No hay frames disponibles aunque has_video_frames=True")
                has_video_frames = False
            else:
                # Procesar frames hasta alcanzar el 40% del total (máximo)
                frames_to_process = min(len(video_frame_files), max_video_frames)
                
                for idx, frame_file in enumerate(video_frame_files[:frames_to_process]):
                    if total_video_frames >= max_video_frames:
                        logger.info(f"   ⚠️  Límite de {max_video_frames} frames alcanzado")
                        break
                        
                    try:
                        with Image.open(frame_file) as img:
                            if img.mode in ('RGBA', 'P', 'LA'):
                                img = img.convert('RGB')
                            
                            # Redimensionar si es muy grande (optimizar para OpenAI)
                            if max(img.size) > 800:
                                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                            
                            buffered = BytesIO()
                            img.save(buffered, format="JPEG", quality=85, optimize=True)
                            b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                            
                            content_blocks.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64}",
                                    "detail": "high"
                                }
                            })
                            total_video_frames += 1
                            
                            if total_video_frames % 5 == 0:
                                logger.info(f"   ✓ Procesados {total_video_frames}/{max_video_frames} frames...")
                                
                    except Exception as e:
                        logger.error(f"   ✗ Error procesando frame {frame_file.name}: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
                
                if total_video_frames == 0:
                    logger.warning(f"   ⚠️  NO SE PROCESARON frames de video - revisar archivos")
                    has_video_frames = False
                else:
                    logger.info(f"   ✅ Total frames de video procesados: {total_video_frames}/{max_video_frames}")
        else:
            if not video_frames_dir.exists():
                logger.info(f"   ℹ️  Directorio de frames no existe: {video_frames_dir}")
            logger.warning(f"   ⚠️  NO HAY frames de video disponibles - balance será 100% imágenes estáticas")
            
        # Ajustar proporción de imágenes estáticas si tenemos frames de video
        if total_video_frames > 0:
            # Si tenemos frames, ajustar el límite de imágenes estáticas
            remaining_slots = MAX_IMAGES - total_video_frames
            max_static_images = min(max_static_images, remaining_slots)
            logger.info(f"   📊 Ajuste de proporción: {total_video_frames} frames ({int(total_video_frames/MAX_IMAGES*100)}%) + hasta {max_static_images} imágenes ({int(max_static_images/MAX_IMAGES*100)}%)")
        
        # SEGUNDO: Procesar imágenes estáticas (60% o el resto disponible)
        logger.info(f"\n   🖼️  PASO 6.2: Procesando hasta {max_static_images} imágenes estáticas...")
        
        # Filtrar imágenes (excluir videos)
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']
        image_files = [
            f for f in media_dir.iterdir() 
            if f.is_file() 
            and f.suffix.lower() in image_extensions
            and f.suffix.lower() not in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.flv', '.wmv']  # Excluir videos
        ]
        
        logger.info(f"   📊 {len(image_files)} imágenes estáticas encontradas")
        
        if not image_files:
            logger.warning(f"   ⚠️  No se encontraron imágenes estáticas en {media_dir}")
        else:
            # Ordenar por tamaño o nombre para consistencia
            image_files = sorted(image_files, key=lambda x: x.stat().st_size, reverse=True)
            
            for img_file in image_files:
                if total_imgs >= max_static_images:
                    logger.info(f"   ⚠️  Límite de {max_static_images} imágenes alcanzado")
                    break
                
                try:
                    with Image.open(img_file) as img:
                        # Validar que sea realmente una imagen válida
                        img.verify()
                        
                    # Reabrir porque verify() cierra la imagen
                    with Image.open(img_file) as img:
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # Redimensionar si es muy grande (optimizar para OpenAI)
                        if max(img.size) > 800:
                            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                        
                        buffered = BytesIO()
                        img.save(buffered, format="JPEG", quality=85, optimize=True)
                        b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        
                        content_blocks.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "high"
                            }
                        })
                        total_imgs += 1
                        
                        if total_imgs % 10 == 0:
                            logger.info(f"   ✓ Procesadas {total_imgs}/{max_static_images} imágenes...")
                            
                except Exception as e:
                    logger.warning(f"   ⚠️  Error procesando imagen {img_file.name}: {e}")
                    # Continuar con la siguiente imagen
        
        logger.info(f"   ✅ Total imágenes estáticas procesadas: {total_imgs}/{max_static_images}")
        
        # Validar balance: asegurar que hay frames si debería haberlos
        if total_video_frames == 0 and has_video_frames:
            logger.error(f"   ❌ ERROR: Se esperaban frames de video pero no se procesaron")
            logger.error(f"   📁 Verificando directorio: {video_frames_dir}")
            if video_frames_dir.exists():
                logger.error(f"   📂 Contenido: {list(video_frames_dir.iterdir())}")
        
        # PASO 7: Enviar a OpenAI con Base64
        logger.info("\n🤖 PASO 7: Enviando a OpenAI...")
        logger.info(f"   📊 Total: {total_imgs} imágenes + {total_video_frames} frames de video")
        logger.info(f"   📊 Balance: {int((total_video_frames/(total_imgs+total_video_frames)*100) if (total_imgs+total_video_frames) > 0 else 0)}% frames, {int((total_imgs/(total_imgs+total_video_frames)*100) if (total_imgs+total_video_frames) > 0 else 0)}% imágenes")
        
        total_assets = total_imgs + total_video_frames
        if total_assets == 0:
            raise HTTPException(400, "No se procesó ninguna multimedia")
        
        # Validar que tenemos contenido para enviar
        if not content_blocks:
            raise HTTPException(400, "No se preparó contenido para enviar a OpenAI")
        
        # Validar que tenemos al menos texto o imágenes
        has_text = any(block.get("type") == "text" for block in content_blocks)
        has_images = any(block.get("type") == "image_url" for block in content_blocks)
        
        if not has_text:
            logger.warning("   ⚠️  No hay contenido de texto, agregando prompt mínimo...")
            content_blocks.insert(0, {
                "type": "text",
                "text": "Analiza estos anuncios publicitarios de Facebook de manera PROFUNDA y DETALLADA. TODO en ESPAÑOL."
            })
        
        if not has_images:
            raise HTTPException(400, f"No se encontraron imágenes para analizar (total assets: {total_assets})")
        
        logger.info(f"   📊 Payload preparado: {len([b for b in content_blocks if b.get('type') == 'text'])} bloques de texto, {len([b for b in content_blocks if b.get('type') == 'image_url'])} imágenes")
        
        # Validar formato del payload antes de enviar
        try:
            import json as json_validate
            # Intentar serializar para validar formato
            json_validate.dumps(content_blocks)
            logger.info("   ✅ Formato del payload validado correctamente")
        except Exception as e:
            logger.error(f"   ❌ Error validando formato del payload: {e}")
            raise HTTPException(500, f"Error en formato del payload: {e}")
        
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto analista de marketing digital y publicidad. IMPORTANTE: Toda tu respuesta debe ser en ESPAÑOL. Debes analizar anuncios publicitarios de manera profesional y proporcionar análisis profundos y detallados. Retorna ÚNICAMENTE un objeto JSON válido sin texto adicional antes o después del JSON."
                    },
                    {"role": "user", "content": content_blocks}
                ],
                response_format={"type": "json_object"}
                # Sin límite de max_tokens para permitir respuesta completa
            )
        except Exception as e:
            logger.error(f"   ❌ Error llamando a OpenAI: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"   📋 Traceback: {traceback.format_exc()}")
            raise HTTPException(500, f"Error en llamada a OpenAI: {str(e)}")
        
        analysis = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0
        
        logger.info(f"   📝 Respuesta recibida: {len(analysis) if analysis else 0} caracteres, {tokens_used} tokens usados")
        
        # Verificar si OpenAI rechazó la solicitud o devolvió respuesta vacía
        if not analysis or len(analysis.strip()) == 0:
            logger.error(f"   ❌ OpenAI devolvió respuesta VACÍA")
            raise HTTPException(
                status_code=500,
                detail="OpenAI devolvió una respuesta vacía. Verifica que el contenido enviado sea válido."
            )
        
        if "no puedo ayudar" in analysis.lower() or "sorry" in analysis.lower() or "cannot" in analysis.lower() or "i can't" in analysis.lower():
            logger.error(f"   ❌ OpenAI rechazó la solicitud: {analysis[:200]}")
            # Guardar respuesta para debugging
            raw_path = run_dir / "reports" / f"{run_id}_rejected_response.txt"
            raw_path.parent.mkdir(exist_ok=True, parents=True)
            with open(raw_path, 'w', encoding='utf-8') as f:
                f.write(analysis)
            logger.error(f"   📄 Respuesta rechazada guardada en: {raw_path}")
            raise HTTPException(
                status_code=500,
                detail="OpenAI rechazó la solicitud. Esto puede deberse a filtros de contenido. Respuesta guardada para revisión."
            )
        
        # Parsear JSON
        analysis_data = None
        try:
            analysis_data = json.loads(analysis)
            logger.info("   ✅ JSON parseado correctamente")
        except json.JSONDecodeError as e:
            logger.warning(f"   ⚠️  Error parseando JSON: {e}")
            try:
                from json_repair import loads as repair_loads
                repaired = repair_loads(analysis)
                # Asegurar que sea un dict, no un string
                if isinstance(repaired, str):
                    analysis_data = json.loads(repaired)
                elif isinstance(repaired, dict):
                    analysis_data = repaired
                else:
                    raise ValueError(f"json_repair devolvió un tipo inesperado: {type(repaired)}")
                logger.info(f"   ✅ JSON reparado exitosamente")
            except Exception as repair_error:
                logger.error(f"   ❌ No se pudo reparar JSON: {repair_error}")
                raise HTTPException(500, f"OpenAI no devolvió JSON válido: {repair_error}")
        
        # Verificar que sea un dict
        if not isinstance(analysis_data, dict):
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI response is not a valid JSON object, got {type(analysis_data)}"
            )
        
        # Guardar JSON
        reports_dir = run_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        json_path = reports_dir / f"{run_id}_analysis_complete.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        # Generar PDF
        logger.info("\n📄 Generando PDF...")
        pdf_path = reports_dir / f"Reporte_Analisis_Completo_{run_id}.pdf"
        pdf_generator = PDFGenerator(str(pdf_path))
        final_pdf_path = pdf_generator.generate(analysis_data)
        
        
        logger.info("="*80)
        logger.info("✅ ANÁLISIS COMPLETO FINALIZADO")
        logger.info("="*80)
        
        return {
            "status": "success",
            "run_id": run_id,
            "pdf_path": str(final_pdf_path),
            "json_report": str(json_path),
            "total_ads_in_csv": len(df),
            "total_images_processed": total_imgs,
            "total_video_frames_processed": total_video_frames,
            "tokens_used": tokens_used,
            "dataset_downloaded": not dataset_exists or not media_exists,
            "message": "Análisis completo finalizado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in analyze-url-with-download: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pdf/{run_id}", tags=["ai-analysis"])
async def download_pdf(run_id: str):
    """
    Endpoint para descargar el PDF generado para un run_id.
    
    Busca el PDF en la ruta: {base_dir}/{run_id}/reports/Reporte_Analisis_Completo_{run_id}.pdf
    
    Args:
        run_id: ID del run
        
    Returns:
        FileResponse con el PDF para descarga
    """
    try:
        base_dir = get_facebook_saved_base()
        run_dir = base_dir / run_id
        reports_dir = run_dir / "reports"
        pdf_filename = f"Reporte_Analisis_Completo_{run_id}.pdf"
        pdf_path = reports_dir / pdf_filename
        
        if not pdf_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"PDF no encontrado para run_id: {run_id}. Asegúrate de haber ejecutado el análisis primero."
            )
        
        return FileResponse(
            path=str(pdf_path),
            filename=pdf_filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando PDF para run_id {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
