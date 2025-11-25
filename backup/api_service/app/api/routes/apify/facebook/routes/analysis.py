"""
AI Analysis Routes
Endpoints para análisis completo con IA (Gemini)
"""
import threading
import socketserver
import http.server
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any
import os
from pyngrok import ngrok
from datetime import datetime
import logging
from pathlib import Path

from ..models.schemas import AnalyzeCampaignRequest
from ..utils.config import get_facebook_saved_base, get_gcs_service
from ..analysis import (
    scrape_and_prepare_run,
    analyze_campaign_with_gemini,
    compile_latex_to_pdf,
    build_manifest_from_gcs
)
from ..analysis.pdf_generator import create_pdf_from_analysis
from ..analysis.prompts import DEFAULT_PROMPT

# Configurar logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# Servidor HTTP para archivos locales


def start_local_file_server(directory, port=8000):
    handler = http.server.SimpleHTTPRequestHandler
    os.chdir(directory)
    httpd = socketserver.TCPServer(("", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


@router.post('/upload-local-files', tags=["ai-analysis"], summary="Sube archivos locales y expone URLs públicas para AI")
async def upload_local_files(files: list[UploadFile] = File(...)):
    """
    Sube archivos locales, los expone por HTTP y retorna URLs públicas para análisis con OpenAI Vision.
    """
    # Carpeta temporal para guardar archivos
    temp_dir = "temp_uploaded_files"
    os.makedirs(temp_dir, exist_ok=True)
    saved_files = []
    for file in files:
        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        saved_files.append(file_path)

    # Iniciar servidor local en el directorio de archivos
    port = 8000
    httpd, thread = start_local_file_server(temp_dir, port)

    # Exponer el puerto con pyngrok
    public_url = ngrok.connect(port)

    # Construir URLs públicas para cada archivo
    public_file_urls = [
        f"{public_url}/{os.path.basename(f)}" for f in saved_files]

    return {
        "status": "success",
        "public_url": public_url,
        "file_urls": public_file_urls,
        "note": "Las URLs estarán activas mientras el túnel y el servidor local estén corriendo."
    }


@router.post(
    '/analyze-campaign-from-bucket',
    tags=["ai-analysis"],
    summary="Análisis con IA desde Bucket GCS"
)
async def analyze_campaign_from_bucket(run_id: str) -> Dict[str, Any]:
    """
    Análisis completo con IA desde archivos ya subidos en GCS

    **Uso simple**: Solo proporciona el run_id de archivos ya en el bucket

    Este endpoint:
    1. Verifica que el run_id exista en Google Cloud Storage
    2. Obtiene las URLs públicas de los archivos del manifest
    3. Analiza con Gemini AI usando el prompt configurado
    4. Genera reporte JSON + código LaTeX
    5. Compila LaTeX a PDF automáticamente
    6. Guarda resultados localmente

    Args:
        run_id: ID del run cuyos archivos están en GCS

    Returns:
        JSON con análisis completo, scores, recomendaciones y código LaTeX

    Tiempo estimado: 30-90 segundos (solo análisis con IA)
    """
    logger.info("="*80)
    logger.info("🚀 INICIANDO ANÁLISIS DESDE BUCKET GCS")
    logger.info("="*80)
    logger.info(f"📋 Run ID: {run_id}")

    try:
        # PASO 1: Verificar Gemini
        logger.info("\n📡 PASO 1/6: Verificando servicio Gemini AI...")
        try:
            from app.services.gemini_service import GeminiService
            gemini_service = GeminiService()
            logger.info("   ✅ Gemini AI disponible")
        except Exception as e:
            logger.error(f"   ❌ Error verificando Gemini: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Gemini AI not available: {str(e)}"
            )

        # PASO 2: Verificar GCS
        logger.info("\n☁️  PASO 2/6: Verificando Google Cloud Storage...")
        gcs_service = get_gcs_service()
        if gcs_service is None:
            logger.error("   ❌ GCS service no configurado")
            raise HTTPException(
                status_code=503,
                detail="GCS service not configured"
            )
        logger.info("   ✅ GCS service disponible")

        # PASO 3: Construir manifest desde GCS
        logger.info("\n📦 PASO 3/6: Construyendo manifest desde bucket...")
        logger.info(f"   - Buscando archivos en bucket para run: {run_id}")
        try:
            manifest_data = build_manifest_from_gcs(run_id, gcs_service)
            logger.info(f"   ✅ Manifest construido")
            logger.info(
                f"   ✅ Anuncios encontrados: {len(manifest_data.get('ads', []))}")
        except Exception as e:
            logger.error(f"   ❌ Error construyendo manifest: {str(e)}")
            raise HTTPException(
                status_code=404,
                detail=f"Error obteniendo datos del bucket: {str(e)}"
            )

        # PASO 4: Analizar con Gemini
        logger.info("\n🤖 PASO 4/6: Analizando con Gemini AI...")
        try:
            analysis_prompt = os.getenv('PROMPT', DEFAULT_PROMPT)
            logger.info(
                f"   - Usando prompt por defecto ({len(analysis_prompt)} chars)")

            base = get_facebook_saved_base()
            reports_dir = base / 'reports_json'

            analysis_json = analyze_campaign_with_gemini(
                run_id=run_id,
                manifest_data=manifest_data,
                analysis_prompt=analysis_prompt,
                gemini_service=gemini_service,
                reports_dir=reports_dir,
                source="gcs_bucket"
            )
            logger.info("   ✅ Análisis completado")
        except Exception as e:
            logger.error(f"   ❌ Error en análisis: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error en análisis IA: {str(e)}"
            )

        # PASO 5: Guardar resultados
        logger.info("\n💾 PASO 5/6: Guardando resultados...")
        try:
            from ..analysis.gemini_analyzer import save_analysis_results

            saved_files = save_analysis_results(
                run_id=run_id,
                analysis_json=analysis_json,
                reports_dir=reports_dir,
                source="gcs_bucket"
            )
            logger.info(f"   ✅ JSON: {saved_files['report_filename']}")
            logger.info(f"   ✅ LaTeX: {saved_files['latex_filename']}")
        except Exception as e:
            logger.error(f"   ❌ Error guardando: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error guardando archivos: {str(e)}"
            )

        # PASO 6: Compilar PDF
        logger.info("\n📄 PASO 6/6: Compilando PDF...")
        pdf_filename = None
        pdf_generated = False
        pdf_error = None

        if saved_files['latex_path']:
            try:
                pdf_result = compile_latex_to_pdf(
                    saved_files['latex_path'],
                    reports_dir
                )
                pdf_filename = pdf_result['pdf_filename']
                pdf_generated = pdf_result['success']
                pdf_error = pdf_result['error']

                if pdf_generated:
                    logger.info(f"   ✅ PDF: {pdf_filename}")
                else:
                    logger.warning(f"   ⚠️  PDF no generado: {pdf_error}")
            except Exception as e:
                logger.error(f"   ❌ Error PDF: {str(e)}")
                pdf_error = str(e)

        logger.info("\n" + "="*80)
        logger.info("🎉 ANÁLISIS DESDE BUCKET COMPLETADO")
        logger.info("="*80)

        return {
            'status': 'success',
            'run_id': run_id,
            'total_ads_analyzed': len(manifest_data.get('ads', [])),
            'report_path': str(saved_files['report_path']),
            'report_filename': saved_files['report_filename'],
            'latex_file': saved_files['latex_filename'],
            'pdf_file': pdf_filename,
            'pdf_generated': pdf_generated,
            'pdf_error': pdf_error,
            'analysis_summary': {
                'best_performer': analysis_json.get(
                    'campaign_summary', {}
                ).get('best_performer'),
                'generated_at': datetime.now().isoformat()
            },
            'full_analysis': analysis_json
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"\n❌ ERROR INESPERADO: {str(e)}")
        logger.exception("Traceback:")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing from bucket: {str(e)}"
        )


@router.post(
    '/analyze-campaign-with-ai',
    tags=["ai-analysis"],
    summary="Análisis Completo con IA y archivos locales"
)
async def analyze_campaign_with_ai(
    request: AnalyzeCampaignRequest,
    files: list[UploadFile] = File(None)
) -> Dict[str, Any]:
    """
    Análisis completo end-to-end de campaña con IA

    **Uso simple**: Solo pega la URL de Facebook Ads Library y listo!

    Flujo automático:
    1. Scrape anuncios desde la URL
    2. Identifica los top N mejores anuncios (por score heurístico)
    3. Descarga archivos multimedia
    4. Sube todo a Google Cloud Storage
    5. Analiza con Gemini AI (prompt personalizable)
    6. Genera reporte JSON + código LaTeX para PDF
    7. Compila LaTeX a PDF automáticamente
    8. Guarda resultados localmente

    Args:
        request: {
            "url": "https://facebook.com/ads/library/?id=...",
            "custom_prompt": "Analiza como experto...",  # Opcional
            "count": 100,  # Opcional (default: 100)
            "top": 10  # Opcional (default: 10)
        }

    Returns:
        JSON con análisis completo, scores, recomendaciones y código LaTeX

    Tiempo estimado: 2-5 minutos
    """
    logger.info("="*80)
    logger.info("🚀 INICIANDO ANÁLISIS COMPLETO DE CAMPAÑA CON IA")
    logger.info("="*80)
    logger.info(f"📋 Parámetros recibidos:")
    logger.info(f"   - URL: {request.url}")

    logger.info(f"   - Count: {request.count or 100}")
    logger.info(f"   - Top: {request.top or 10}")
    logger.info(
        f"   - Custom prompt: {'Sí' if request.custom_prompt else 'No'}")
    if files:
        logger.info(f"   - Archivos locales recibidos: {len(files)}")

    try:
        # PASO 1: Verificar OpenAI
        logger.info("\n📡 PASO 1/7: Verificando servicio OpenAI...")
        try:
            from openai import OpenAI

            api_key = os.getenv("OPEN_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=503,
                    detail="OPEN_API_KEY no configurada en .env"
                )

            openai_client = OpenAI(api_key=api_key)
            logger.info("   ✅ OpenAI disponible y configurado")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"   ❌ Error verificando OpenAI: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"OpenAI not available: {str(e)}"
            )

        # PASO EXTRA: Si hay archivos locales, exponerlos y obtener URLs públicas
        public_file_urls = []
        if files:
            temp_dir = "temp_uploaded_files"
            os.makedirs(temp_dir, exist_ok=True)
            saved_files = []
            for file in files:
                file_path = os.path.join(temp_dir, file.filename)
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                saved_files.append(file_path)

            port = 8000
            httpd, thread = start_local_file_server(temp_dir, port)
            public_url = ngrok.connect(port)
            public_file_urls = [
                f"{public_url}/{os.path.basename(f)}" for f in saved_files]
            logger.info(f"   ✅ Archivos locales expuestos en: {public_url}")

        # PASO 2: Ejecutar workflow completo (scrape + prepare)
        logger.info("\n🔍 PASO 2/7: Ejecutando scrape y preparación...")
        logger.info("   - Extrayendo anuncios de Facebook")
        logger.info("   - Seleccionando top mejores anuncios")
        logger.info("   - Descargando multimedia")
        try:
            workflow_result = await scrape_and_prepare_run(
                url=request.url,
                count=request.count or 100,
                top=request.top or 10
            )
            run_id = workflow_result['run_id']
            manifest_data = workflow_result['manifest']
            logger.info(f"   ✅ Scrape completado - Run ID: {run_id}")
            logger.info(
                f"   ✅ Anuncios procesados: {len(manifest_data.get('ads', []))}")
        except Exception as e:
            logger.error(f"   ❌ Error en scrape/preparación: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error en scrape: {str(e)}"
            )

        # PASO 3: Preparar prompt
        logger.info("\n📝 PASO 3/7: Preparando prompt de análisis...")
        custom_prompt = request.custom_prompt
        env_prompt = os.getenv('PROMPT', DEFAULT_PROMPT)
        analysis_prompt = custom_prompt or env_prompt
        prompt_source = "personalizado" if custom_prompt else "por defecto"
        logger.info(f"   ✅ Usando prompt {prompt_source}")
        logger.info(
            f"   ✅ Longitud del prompt: {len(analysis_prompt)} caracteres")

        # PASO 4: Analizar con OpenAI
        logger.info("\n🤖 PASO 4/7: Analizando campaña con OpenAI Vision...")
        logger.info("   - Enviando datos a OpenAI (GPT-4 Vision)")
        logger.info("   - Esperando análisis detallado...")
        try:
            base = get_facebook_saved_base()
            reports_dir = base / 'reports_json'

            # Construir mensaje único con todas las imágenes
            content = [
                {
                    "type": "text",
                    "text": f"{analysis_prompt}\n\nAnaliza los siguientes anuncios:"
                }
            ]

            # Agregar cada anuncio con sus imágenes
            for ad in manifest_data.get('ads', []):
                ad_id = ad.get('ad_id', 'N/A')
                files_ad = ad.get('files', [])

                content.append({
                    "type": "text",
                    "text": f"\n--- Anuncio ID: {ad_id} ---"
                })

                # Agregar imágenes del anuncio
                image_count = 0
                for file_info in files_ad:
                    if file_info.get('type') == 'image':
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": file_info['url']
                            }
                        })
                        image_count += 1

                logger.info(f"   - Anuncio {ad_id}: {image_count} imágenes")

            # Si hay archivos locales, agregarlos también
            if public_file_urls:
                for url in public_file_urls:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": url}
                    })
                logger.info(
                    f"   - Imágenes locales agregadas al análisis: {len(public_file_urls)}")

            messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]

            # Llamar a OpenAI GPT-4 Vision (modelo actualizado)
            ads_count = len(manifest_data.get('ads', []))
            logger.info(f"   - Total anuncios: {ads_count}")
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=4096,
                temperature=0.5  # Balance precisión-creatividad para análisis
            )

            analysis_text = response.choices[0].message.content
            analysis_json = {
                "run_id": run_id,
                "analysis": analysis_text,
                "model": "gpt-4o",
                "ads_count": len(manifest_data.get('ads', [])),
                "manifest": manifest_data,
                "local_files": public_file_urls
            }

            logger.info("   ✅ Análisis con IA completado")
            logger.info("   ✅ Respuesta recibida de OpenAI")
        except Exception as e:
            logger.error(f"   ❌ Error en análisis con OpenAI: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error en análisis IA: {str(e)}"
            )

        # PASO 5: Guardar resultados
        logger.info("\n💾 PASO 5/7: Guardando resultados...")
        try:
            import json
            reports_dir.mkdir(parents=True, exist_ok=True)

            # Guardar JSON
            report_filename = f"{run_id}_analysis.json"
            report_path = reports_dir / report_filename
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_json, f, ensure_ascii=False, indent=2)

            saved_files = {
                'report_filename': report_filename,
                'report_path': str(report_path),
                'latex_filename': None
            }

            logger.info(f"   ✅ JSON guardado: {report_filename}")
            logger.info(f"   ✅ Ruta: {report_path}")
        except Exception as e:
            logger.error(f"   ❌ Error guardando resultados: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error guardando archivos: {str(e)}"
            )

        # PASO 6: (Saltado - no se genera LaTeX/PDF con OpenAI)
        logger.info("\n📄 PASO 6/7: Generación de PDF...")
        logger.info("   ⚠️  Paso omitido (solo se genera JSON con OpenAI)")

        # PASO 7: Resultado final
        logger.info("\n✨ PASO 7/7: Preparando respuesta final...")
        logger.info("="*80)
        logger.info("🎉 ANÁLISIS COMPLETADO EXITOSAMENTE")
        logger.info("="*80)
        logger.info("📊 Resumen:")
        ads_count = len(manifest_data.get('ads', []))
        logger.info(f"   - Run ID: {run_id}")
        logger.info(f"   - Anuncios analizados: {ads_count}")
        logger.info("   - Reporte JSON: ✅")
        logger.info("   - Proveedor: OpenAI (gpt-3.5-turbo)")
        logger.info("="*80)

        return {
            'status': 'success',
            'run_id': run_id,
            'total_ads_analyzed': len(manifest_data.get('ads', [])),
            'report_path': str(saved_files['report_path']),
            'report_filename': saved_files['report_filename'],
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'analysis_summary': {
                'generated_at': datetime.now().isoformat()
            },
            'full_analysis': analysis_json
        }

    except HTTPException:
        logger.error("\n❌ Error HTTP capturado, reenviando...")
        raise
    except Exception as e:
        logger.error(f"\n❌ ERROR INESPERADO: {str(e)}")
        logger.exception("Traceback completo:")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )


@router.post(
    '/analyze-from-run-id',
    tags=["ai-analysis"],
    summary="Análisis con OpenAI desde run_id existente"
)
async def analyze_from_run_id(run_id: str) -> Dict[str, Any]:
    """
    Análisis completo con OpenAI desde un run_id que ya tiene datos.

    Este endpoint:
    1. Toma un run_id de un scraping exitoso previo
    2. Analiza el dataset local
    3. Descarga multimedia de los top anuncios
    4. Sube archivos a GCS
    5. Construye manifest con URLs públicas
    6. Analiza con OpenAI GPT-4o Vision
    7. Guarda resultados en JSON

    Args:
        run_id: ID del run ya existente con datos scrapeados

    Returns:
        JSON con análisis completo y manifest

    Tiempo estimado: 1-3 minutos
    """
    logger.info("="*80)
    logger.info("🚀 ANÁLISIS DESDE RUN_ID EXISTENTE")
    logger.info("="*80)
    logger.info(f"📋 RUN_ID: {run_id}")

    try:
        # PASO 1: Verificar OpenAI
        logger.info("\n📡 PASO 1/7: Verificando configuración OpenAI...")
        from openai import OpenAI

        api_key = os.getenv("OPEN_API_KEY")
        if not api_key:
            logger.error(f"   ❌ RUN_ID {run_id}: OPEN_API_KEY no configurada")
            raise HTTPException(
                status_code=503,
                detail="OPEN_API_KEY no configurada"
            )

        openai_client = OpenAI(api_key=api_key)
        logger.info(f"   ✅ RUN_ID {run_id}: OpenAI configurado correctamente")

        # PASO 2: Verificar si ya existe en GCS
        logger.info("\n☁️  PASO 2/7: Verificando archivos en GCS...")
        gcs_service = get_gcs_service()
        if not gcs_service:
            logger.error(f"   ❌ RUN_ID {run_id}: GCS no configurado")
            raise HTTPException(503, "GCS no configurado")

        bucket_name = gcs_service.default_bucket_name
        gcs_prefix = f'runs/{run_id}/prepared/'

        logger.info(
            f"   🔍 RUN_ID {run_id}: Buscando en gs://{bucket_name}/{gcs_prefix}")

        # Listar archivos en GCS
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=gcs_prefix))

        manifest = {'run_id': run_id, 'ads': []}
        already_in_gcs = False

        if blobs:
            logger.info(
                f"   ✅ RUN_ID {run_id}: Encontrados {len(blobs)} archivos en GCS")
            logger.info(
                f"   ℹ️  RUN_ID {run_id}: Usando archivos existentes (sin re-procesar)")
            already_in_gcs = True

            # Construir manifest desde GCS
            media_by_ad = {}
            for blob in blobs:
                # Extraer ad_id: runs/{run_id}/prepared/{ad_id}/{filename}
                parts = blob.name.split('/')
                if len(parts) >= 4:
                    ad_id = parts[3]
                    if ad_id not in media_by_ad:
                        media_by_ad[ad_id] = []
                        logger.debug(
                            f"   📁 RUN_ID {run_id}: Ad ID {ad_id} detectado")

                    public_url = (
                        f"https://storage.googleapis.com/"
                        f"{bucket_name}/{blob.name}"
                    )
                    is_video = blob.name.endswith('.mp4')
                    file_type = 'video' if is_video else 'image'

                    media_by_ad[ad_id].append({
                        'url': public_url,
                        'type': file_type
                    })

            for ad_id, files in media_by_ad.items():
                manifest['ads'].append({
                    'ad_id': ad_id,
                    'files': files
                })

            logger.info(
                f"   ✅ RUN_ID {run_id}: Manifest construido desde GCS "
                f"({len(manifest['ads'])} anuncios, "
                f"{sum(len(ad['files']) for ad in manifest['ads'])} archivos)"
            )
        else:
            logger.warning(
                f"   ⚠️  RUN_ID {run_id}: No encontrado en GCS"
            )
            logger.info(
                f"   🔄 RUN_ID {run_id}: Iniciando preparación desde datos locales..."
            )

        # PASO 3: Si no está en GCS, procesar localmente
        if not already_in_gcs:
            logger.info("\n📊 PASO 3/7: Procesando dataset local...")
            from pathlib import Path
            from app.processors.facebook.analyze_dataset import (
                analyze, analyze_jsonl
            )

            base_dir = get_facebook_saved_base()
            run_dir = base_dir / run_id

            logger.info(f"   🔍 RUN_ID {run_id}: Buscando en {run_dir}")

            if not run_dir.exists():
                logger.error(
                    f"   ❌ RUN_ID {run_id}: No encontrado en local ni en GCS"
                )
                logger.error(f"   📂 RUN_ID {run_id}: Ruta buscada: {run_dir}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Run ID {run_id} no encontrado localmente ni en GCS"
                )

            logger.info(f"   ✅ RUN_ID {run_id}: Directorio encontrado")

            csv_path = run_dir / f"{run_id}.csv"
            jsonl_path = run_dir / f"{run_id}.jsonl"

            stats = {}
            if csv_path.exists():
                logger.info(f"   📄 RUN_ID {run_id}: Procesando CSV...")
                stats = analyze(csv_path)
                logger.info(
                    f"   ✅ RUN_ID {run_id}: CSV analizado "
                    f"({len(stats)} anuncios encontrados)"
                )
            elif jsonl_path.exists():
                logger.info(f"   📄 RUN_ID {run_id}: Procesando JSONL...")
                stats = analyze_jsonl(jsonl_path)
                logger.info(
                    f"   ✅ RUN_ID {run_id}: JSONL analizado "
                    f"({len(stats)} anuncios encontrados)"
                )
            else:
                logger.error(
                    f"   ❌ RUN_ID {run_id}: No se encontró CSV ni JSONL"
                )
                logger.error(f"   📂 CSV esperado: {csv_path}")
                logger.error(f"   📂 JSONL esperado: {jsonl_path}")
                raise HTTPException(
                    status_code=404,
                    detail="No se encontró CSV ni JSONL en directorio local"
                )

            # Tomar top 10
            items = sorted(
                stats.values(),
                key=lambda x: x.get('score', 0),
                reverse=True
            )
            top_ads = [it.get('ad_id') for it in items[:10]]
            logger.info(
                f"   ✅ RUN_ID {run_id}: Top 10 anuncios seleccionados "
                f"(IDs: {', '.join(map(str, top_ads[:3]))}...)"
            )

            # PASO 4: Descargar multimedia
            logger.info("\n📥 PASO 4/7: Descargando multimedia...")
            from app.processors.facebook.download_images_from_csv import (
                make_session,
                download_one,
                iter_csv_snapshot_rows,
                extract_urls_from_snapshot
            )
            from concurrent.futures import ThreadPoolExecutor, as_completed

            media_dir = run_dir / 'media'
            media_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"   📁 RUN_ID {run_id}: Directorio media: {media_dir}")

            session = make_session()

            downloaded = 0
            total_urls = 0
            if csv_path.exists():
                logger.info(
                    f"   🔄 RUN_ID {run_id}: Extrayendo URLs de multimedia..."
                )
                with ThreadPoolExecutor(max_workers=6) as ex:
                    futures = []
                    for row, snapshot in iter_csv_snapshot_rows(csv_path):
                        ad_id = (
                            row.get('ad_archive_id') or
                            row.get('ad_id') or
                            'unknown'
                        )
                        if ad_id not in top_ads:
                            continue
                        if not snapshot:
                            continue
                        urls = extract_urls_from_snapshot(snapshot)
                        total_urls += len(urls[:5])
                        for u in urls[:5]:
                            futures.append(
                                ex.submit(
                                    download_one,
                                    session,
                                    u,
                                    media_dir,
                                    prefix=ad_id
                                )
                            )

                    logger.info(
                        f"   🌐 RUN_ID {run_id}: Descargando {total_urls} archivos..."
                    )

                    for fut in as_completed(futures):
                        url, path = fut.result()
                        if path:
                            downloaded += 1
                            if downloaded % 10 == 0:
                                logger.debug(
                                    f"   📥 RUN_ID {run_id}: "
                                    f"Descargados {downloaded}/{total_urls}"
                                )

            logger.info(
                f"   ✅ RUN_ID {run_id}: {downloaded} archivos descargados "
                f"de {total_urls} URLs procesadas"
            )

            # PASO 5: Preparar archivos
            logger.info("\n📂 PASO 5/7: Preparando archivos...")
            import shutil

            prepared_dir = run_dir / 'prepared'
            prepared_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"   📁 RUN_ID {run_id}: Directorio prepared: {prepared_dir}")

            files_prepared = 0
            for ad_id in top_ads:
                ad_dir = prepared_dir / str(ad_id)
                ad_dir.mkdir(parents=True, exist_ok=True)

                matched = [
                    p for p in media_dir.iterdir()
                    if p.is_file() and p.name.startswith(str(ad_id))
                ]

                logger.debug(
                    f"   📋 RUN_ID {run_id}: Ad {ad_id} - "
                    f"{len(matched)} archivos encontrados"
                )

                for p in matched[:5]:
                    shutil.copy2(p, ad_dir / p.name)
                    files_prepared += 1

            logger.info(
                f"   ✅ RUN_ID {run_id}: {files_prepared} archivos preparados "
                f"({len(top_ads)} anuncios)"
            )

            # PASO 6: Subir a GCS
            logger.info("\n☁️  PASO 6/7: Subiendo a GCS...")
            logger.info(
                f"   🌐 RUN_ID {run_id}: "
                f"Destino: gs://{bucket_name}/{gcs_prefix}"
            )

            uploaded_files = []
            total_files = sum(
                1 for _ in prepared_dir.rglob('*')
                if _.is_file()
            )
            logger.info(
                f"   📤 RUN_ID {run_id}: Subiendo {total_files} archivos..."
            )

            for file_path in prepared_dir.rglob('*'):
                if not file_path.is_file():
                    continue

                relative_path = file_path.relative_to(prepared_dir)
                blob_name = f'{gcs_prefix}{relative_path}'.replace('\\', '/')

                logger.debug(
                    f"   📤 RUN_ID {run_id}: Subiendo {file_path.name}"
                )

                result = gcs_service.upload_file(
                    local_path=str(file_path),
                    blob_name=blob_name,
                    bucket_name=bucket_name
                )
                uploaded_files.append({
                    'blob_name': blob_name,
                    'public_url': result['public_url'],
                    'ad_id': file_path.parent.name
                })

            logger.info(
                f"   ✅ RUN_ID {run_id}: {len(uploaded_files)} archivos subidos "
                f"a GCS correctamente"
            )

            # Construir manifest desde archivos subidos
            media_by_ad = {}

            for file_info in uploaded_files:
                ad_id = file_info['ad_id']
                if ad_id not in media_by_ad:
                    media_by_ad[ad_id] = []

                is_video = file_info['blob_name'].endswith('.mp4')
                file_type = 'video' if is_video else 'image'
                media_by_ad[ad_id].append({
                    'url': file_info['public_url'],
                    'type': file_type
                })

            for ad_id, files in media_by_ad.items():
                manifest['ads'].append({
                    'ad_id': ad_id,
                    'files': files
                })

            logger.info(
                f"   ✅ RUN_ID {run_id}: Manifest construido "
                f"({len(manifest['ads'])} anuncios, "
                f"{sum(len(ad['files']) for ad in manifest['ads'])} archivos)"
            )

        # Validar manifest
        if not manifest['ads']:
            logger.error(f"   ❌ RUN_ID {run_id}: Manifest vacío, sin anuncios")
            raise HTTPException(
                status_code=400,
                detail="No hay anuncios en el manifest"
            )

        # PASO 7: Analizar con OpenAI
        logger.info("\n🤖 PASO 7/7: Analizando con OpenAI GPT-4o...")
        logger.info(
            f"   📊 RUN_ID {run_id}: Enviando {len(manifest['ads'])} anuncios "
            f"con {sum(len(ad['files']) for ad in manifest['ads'])} imágenes"
        )

        # Cargar prompt con fallback chain: .env PROMPT → prompt.txt → DEFAULT_PROMPT
        env_prompt = os.getenv('PROMPT')
        if not env_prompt:
            prompt_file_name = os.getenv('PROMPT_FILE', 'prompt.txt')
            # 7 niveles para llegar a api_service/ desde analysis.py
            api_service_dir = Path(
                __file__).parent.parent.parent.parent.parent.parent.parent
            prompt_file_path = api_service_dir / prompt_file_name

            logger.info(f"   🔍 Buscando prompt en: {prompt_file_path}")

            if prompt_file_path.exists():
                env_prompt = prompt_file_path.read_text(encoding='utf-8')
                logger.info(
                    f"   ✅ RUN_ID {run_id}: Prompt cargado desde {prompt_file_name} "
                    f"({len(env_prompt)} caracteres)")
            else:
                logger.warning(
                    f"   ⚠️ RUN_ID {run_id}: Archivo {prompt_file_name} no encontrado en {api_service_dir}, "
                    f"usando DEFAULT_PROMPT")
                env_prompt = DEFAULT_PROMPT
        else:
            logger.info(
                f"   📝 RUN_ID {run_id}: Usando prompt del .env ({len(env_prompt)} chars)")

        logger.info(
            f"   📝 RUN_ID {run_id}: Prompt final cargado ({len(env_prompt)} chars)")

        # Construir mensaje con imágenes
        content = [
            {
                "type": "text",
                "text": f"{env_prompt}\n\nAnaliza los siguientes anuncios:"
            }
        ]

        image_count = 0
        for ad in manifest['ads']:
            ad_id = ad.get('ad_id', 'N/A')
            content.append({
                "type": "text",
                "text": f"\n--- Anuncio ID: {ad_id} ---"
            })

            for file_info in ad.get('files', []):
                if file_info.get('type') == 'image':
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": file_info['url']}
                    })
                    image_count += 1

        logger.info(
            f"   🖼️  RUN_ID {run_id}: Preparadas {image_count} imágenes "
            f"para análisis"
        )

        messages = [{"role": "user", "content": content}]

        logger.info(f"   🚀 RUN_ID {run_id}: Enviando solicitud a OpenAI...")

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=4096,
            temperature=0.5  # Balance precisión-creatividad para análisis
        )

        logger.info(f"   ✅ RUN_ID {run_id}: Respuesta recibida de OpenAI")

        analysis_text = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.info(
            f"   📊 RUN_ID {run_id}: Tokens usados: {tokens_used} "
            f"(análisis: {len(analysis_text)} chars)"
        )

        analysis_json = {
            "run_id": run_id,
            "analysis": analysis_text,
            "model": "gpt-4o",
            "ads_count": len(manifest['ads']),
            "tokens_used": tokens_used,
            "manifest": manifest
        }

        logger.info(f"   ✅ RUN_ID {run_id}: Análisis completado exitosamente")

        # Guardar resultados
        logger.info(f"   💾 RUN_ID {run_id}: Guardando reporte...")

        save_base_dir = get_facebook_saved_base()
        reports_dir = save_base_dir / 'reports_json'
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_filename = f"{run_id}_analysis.json"
        report_path = reports_dir / report_filename

        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_json, f, ensure_ascii=False, indent=2)

        logger.info(
            f"   ✅ RUN_ID {run_id}: Reporte guardado en {report_filename}")
        logger.info("="*80)
        logger.info(f"🎉 RUN_ID {run_id}: ANÁLISIS COMPLETADO EXITOSAMENTE")
        logger.info("="*80)

        return {
            'status': 'success',
            'run_id': run_id,
            'total_ads_analyzed': len(manifest['ads']),
            'report_path': str(report_path),
            'report_filename': report_filename,
            'provider': 'openai',
            'model': 'gpt-4o',
            'analysis_summary': {
                'generated_at': datetime.now().isoformat()
            },
            'full_analysis': analysis_json
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ RUN_ID {run_id}: ERROR EN ANÁLISIS")
        logger.error("="*80)
        logger.error(
            f"   🔴 RUN_ID {run_id}: Tipo de error: {type(e).__name__}")
        logger.error(f"   🔴 RUN_ID {run_id}: Mensaje: {str(e)}")
        logger.exception(f"   📋 RUN_ID {run_id}: Traceback completo:")
        raise HTTPException(
            status_code=500,
            detail=f"Error en análisis de RUN_ID {run_id}: {str(e)}"
        )


@router.post(
    '/analyze-local-only',
    tags=["ai-analysis"],
    summary="Análisis con OpenAI solo con archivos locales (sin GCS)"
)
async def analyze_local_only(
    run_id: str,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Análisis completo con OpenAI usando SOLO archivos locales.
    NO requiere acceso a GCS.

    Este endpoint:
    1. Lee el dataset local (CSV/JSONL)
    2. Analiza y selecciona top N anuncios
    3. Descarga multimedia localmente
    4. Codifica imágenes en base64
    5. Envía a OpenAI para análisis
    6. Retorna JSON con análisis completo

    Args:
        run_id: ID del run con datos locales
        top_n: Número de anuncios a analizar (default: 10)

    Returns:
        JSON con análisis completo

    NO requiere: GCS, credenciales cloud, acceso a bucket
    """
    logger.info("="*80)
    logger.info("🚀 ANÁLISIS LOCAL (SIN GCS)")
    logger.info("="*80)
    logger.info(f"📋 RUN_ID: {run_id}")
    logger.info(f"📊 Top N: {top_n}")

    try:
        # PASO 1: Verificar OpenAI
        logger.info("\n📡 PASO 1/5: Verificando OpenAI...")
        from openai import OpenAI

        api_key = os.getenv("OPEN_API_KEY")
        if not api_key:
            logger.error(f"   ❌ RUN_ID {run_id}: OPEN_API_KEY no configurada")
            raise HTTPException(503, "OPEN_API_KEY no configurada")

        openai_client = OpenAI(api_key=api_key)
        logger.info(f"   ✅ RUN_ID {run_id}: OpenAI configurado")

        # PASO 2: Leer dataset local
        logger.info("\n📊 PASO 2/5: Procesando dataset local...")
        from pathlib import Path
        from app.processors.facebook.analyze_dataset import (
            analyze, analyze_jsonl
        )

        base_dir = get_facebook_saved_base()
        run_dir = base_dir / run_id

        logger.info(f"   🔍 RUN_ID {run_id}: Buscando en {run_dir}")

        if not run_dir.exists():
            logger.error(f"   ❌ RUN_ID {run_id}: Directorio no encontrado")
            raise HTTPException(404, f"Run ID {run_id} no encontrado")

        csv_path = run_dir / f"{run_id}.csv"
        jsonl_path = run_dir / f"{run_id}.jsonl"

        stats = {}
        if csv_path.exists():
            logger.info(f"   📄 RUN_ID {run_id}: Procesando CSV...")
            stats = analyze(csv_path)
            logger.info(f"   ✅ RUN_ID {run_id}: {len(stats)} anuncios")
        elif jsonl_path.exists():
            logger.info(f"   📄 RUN_ID {run_id}: Procesando JSONL...")
            stats = analyze_jsonl(jsonl_path)
            logger.info(f"   ✅ RUN_ID {run_id}: {len(stats)} anuncios")
        else:
            logger.error(f"   ❌ RUN_ID {run_id}: No se encontró dataset")
            raise HTTPException(404, "No se encontró CSV ni JSONL")

        # Seleccionar top N
        items = sorted(
            stats.values(),
            key=lambda x: x.get('score', 0),
            reverse=True
        )
        top_ads = [it.get('ad_id') for it in items[:top_n]]
        logger.info(
            f"   ✅ RUN_ID {run_id}: Top {len(top_ads)} seleccionados"
        )

        # PASO 3: Descargar multimedia
        logger.info("\n📥 PASO 3/5: Descargando multimedia...")
        from app.processors.facebook.download_images_from_csv import (
            make_session,
            download_one,
            iter_csv_snapshot_rows,
            extract_urls_from_snapshot
        )
        from concurrent.futures import ThreadPoolExecutor, as_completed

        media_dir = run_dir / 'media'
        media_dir.mkdir(parents=True, exist_ok=True)
        session = make_session()

        downloaded = 0
        if csv_path.exists():
            with ThreadPoolExecutor(max_workers=6) as ex:
                futures = []
                for row, snapshot in iter_csv_snapshot_rows(csv_path):
                    ad_id = (
                        row.get('ad_archive_id') or
                        row.get('ad_id') or
                        'unknown'
                    )
                    if ad_id not in top_ads:
                        continue
                    if not snapshot:
                        continue
                    urls = extract_urls_from_snapshot(snapshot)
                    for u in urls[:5]:
                        futures.append(
                            ex.submit(
                                download_one,
                                session,
                                u,
                                media_dir,
                                prefix=ad_id
                            )
                        )

                for fut in as_completed(futures):
                    url, path = fut.result()
                    if path:
                        downloaded += 1

        logger.info(f"   ✅ RUN_ID {run_id}: {downloaded} archivos descargados")

        # PASO 4: Codificar multimedia (imágenes + videos)
        logger.info(
            "\n🖼️  PASO 4/5: Procesando multimedia (imágenes + videos)...")
        import base64
        from app.utils.video_utils import extract_frames_from_video

        ads_with_media = []
        total_images = 0
        total_video_frames = 0
        total_videos = 0

        # Primero: detectar TODOS los videos disponibles
        all_videos = [
            p for p in media_dir.iterdir()
            if p.is_file() and p.suffix.lower() in ['.mp4', '.mov', '.avi', '.webm']
        ]
        logger.info(f"   📹 Detectados {len(all_videos)} videos en total")
        if all_videos:
            for v in all_videos[:3]:  # Mostrar primeros 3
                logger.info(f"      - {v.name}")

        for ad_id in top_ads:
            # Buscar archivos del anuncio (con patrón más flexible)
            ad_id_str = str(ad_id)
            matched = [
                p for p in media_dir.iterdir()
                if p.is_file() and (
                    p.name.startswith(ad_id_str + '_') or
                    p.name.startswith(ad_id_str + '.')
                )
            ]

            logger.info(
                f"   🔍 AD {ad_id}: {len(matched)} archivos encontrados")

            media_items = []

            # Procesar multimedia (max 3 archivos por anuncio para velocidad)
            for media_path in matched[:3]:
                file_ext = media_path.suffix.lower()

                # IMÁGENES
                if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    try:
                        with open(media_path, 'rb') as f:
                            img_data = f.read()
                            b64_str = base64.b64encode(
                                img_data).decode('utf-8')

                            mime_type = 'image/jpeg'
                            if file_ext == '.png':
                                mime_type = 'image/png'
                            elif file_ext == '.gif':
                                mime_type = 'image/gif'
                            elif file_ext == '.webp':
                                mime_type = 'image/webp'

                            media_items.append({
                                'type': 'image',
                                'filename': media_path.name,
                                'mime_type': mime_type,
                                'base64': b64_str
                            })
                            total_images += 1
                    except Exception as e:
                        logger.warning(
                            f"   ⚠️  Error con imagen {media_path.name}: {e}")

                # VIDEOS: Extraer 5 frames
                elif file_ext in ['.mp4', '.mov', '.avi', '.webm']:
                    try:
                        logger.info(
                            f"   🎥 Extrayendo frames de {media_path.name}...")
                        frames = extract_frames_from_video(
                            media_path, num_frames=5)

                        if frames:
                            for frame in frames:
                                media_items.append({
                                    'type': 'video_frame',
                                    'source_video': media_path.name,
                                    'frame_number': frame['frame_number'],
                                    'timestamp': frame['timestamp'],
                                    'mime_type': 'image/jpeg',
                                    'base64': frame['base64']
                                })
                                total_video_frames += 1

                            total_videos += 1
                            logger.info(
                                f"      ✅ {len(frames)} frames extraídos")
                    except Exception as e:
                        logger.warning(
                            f"   ⚠️  Error con video {media_path.name}: {e}")

            if media_items:
                ads_with_media.append({
                    'ad_id': ad_id,
                    'media': media_items
                })

        # Si no se procesaron videos pero hay videos disponibles, procesar los primeros
        if total_videos == 0 and all_videos:
            logger.info(
                f"   ⚠️  Videos no asociados a top_ads, procesando {min(2, len(all_videos))} videos...")
            for video_path in all_videos[:2]:
                try:
                    logger.info(
                        f"   🎥 Extrayendo frames de {video_path.name}...")
                    frames = extract_frames_from_video(
                        video_path, num_frames=5)

                    if frames:
                        video_items = []
                        for frame in frames:
                            video_items.append({
                                'type': 'video_frame',
                                'source_video': video_path.name,
                                'frame_number': frame['frame_number'],
                                'timestamp': frame['timestamp'],
                                'mime_type': 'image/jpeg',
                                'base64': frame['base64']
                            })
                            total_video_frames += 1

                        total_videos += 1
                        logger.info(f"      ✅ {len(frames)} frames extraídos")

                        # Agregar como anuncio "extra"
                        ads_with_media.append({
                            'ad_id': f'video_{video_path.stem}',
                            'media': video_items
                        })
                except Exception as e:
                    logger.warning(
                        f"   ⚠️  Error con video {video_path.name}: {e}")

        logger.info(
            f"   ✅ RUN_ID {run_id}: {total_images} imágenes + "
            f"{total_video_frames} frames ({total_videos} videos) - "
            f"{len(ads_with_media)} anuncios"
        )

        if not ads_with_media:
            logger.error(f"   ❌ RUN_ID {run_id}: No hay multimedia")
            raise HTTPException(400, "No se encontró multimedia para analizar")

        # PASO 5: Analizar con OpenAI
        logger.info("\n🤖 PASO 5/5: Analizando con OpenAI...")

        # Cargar prompt con fallback chain: .env PROMPT → prompt.txt → DEFAULT_PROMPT
        env_prompt = os.getenv('PROMPT')
        if not env_prompt:
            prompt_file_name = os.getenv('PROMPT_FILE', 'prompt.txt')
            # 7 niveles para llegar a api_service/ desde analysis.py
            api_service_dir = Path(
                __file__).parent.parent.parent.parent.parent.parent.parent
            prompt_file_path = api_service_dir / prompt_file_name

            logger.info(f"   🔍 Buscando prompt en: {prompt_file_path}")

            if prompt_file_path.exists():
                env_prompt = prompt_file_path.read_text(encoding='utf-8')
                logger.info(
                    f"   ✅ RUN_ID {run_id}: Prompt cargado desde {prompt_file_name} "
                    f"({len(env_prompt)} caracteres)")
            else:
                logger.warning(
                    f"   ⚠️ RUN_ID {run_id}: Archivo {prompt_file_name} no encontrado en {api_service_dir}, "
                    f"usando DEFAULT_PROMPT")
                env_prompt = DEFAULT_PROMPT
        else:
            logger.info(
                f"   📝 RUN_ID {run_id}: Usando prompt del .env ({len(env_prompt)} chars)")

        # Preparar metadatos del CSV para incluir en el prompt
        import csv
        import json as json_module

        csv_metadata = []
        if csv_path.exists():
            logger.info(
                f"   � RUN_ID {run_id}: Extrayendo metadatos del CSV...")
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ad_id = row.get('ad_archive_id') or row.get(
                        'adArchiveID') or row.get('id')
                    if ad_id in [ad['ad_id'] for ad in ads_with_media]:
                        # Incluir solo campos relevantes
                        metadata = {
                            'ad_id': ad_id,
                            'page_name': row.get('page_name', 'N/A'),
                            'ad_creation_time': row.get('ad_creation_time', 'N/A'),
                            'ad_creative_bodies': row.get('ad_creative_bodies', 'N/A'),
                            'ad_creative_link_titles': row.get('ad_creative_link_titles', 'N/A'),
                            'ad_creative_link_descriptions': row.get('ad_creative_link_descriptions', 'N/A'),
                            'impressionsMin': row.get('impressionsMin', 'N/A'),
                            'impressionsMax': row.get('impressionsMax', 'N/A'),
                            'spendMin': row.get('spendMin', 'N/A'),
                            'spendMax': row.get('spendMax', 'N/A'),
                        }
                        csv_metadata.append(metadata)

            logger.info(
                f"   ✅ RUN_ID {run_id}: {len(csv_metadata)} registros de metadatos extraídos")

        # Construir mensaje con prompt + metadatos del CSV + multimedia
        metadata_text = ""
        if csv_metadata:
            metadata_text = "\n\n**DATOS DE ENTRADA - Metadatos del CSV:**\n```json\n"
            metadata_text += json_module.dumps(csv_metadata,
                                               ensure_ascii=False, indent=2)
            metadata_text += "\n```\n"
            logger.info(
                f"   📊 Metadatos CSV incluidos: {len(csv_metadata)} anuncios")

        # Construir texto completo del prompt
        full_prompt_text = env_prompt + metadata_text

        logger.info(
            f"   📝 Longitud prompt completo: {len(full_prompt_text)} caracteres")
        logger.info(
            f"   📝 Primeros 200 chars del prompt: {env_prompt[:200]}...")

        content = [
            {
                "type": "text",
                "text": full_prompt_text
            }
        ]

        # Agregar imágenes y frames de videos de cada anuncio
        media_count = 0
        for ad in ads_with_media:
            ad_id = ad.get('ad_id', 'unknown')
            for media in ad['media']:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media['mime_type']};base64,{media['base64']}"
                    }
                })
                media_count += 1

        logger.info(
            f"   🖼️  Total elementos multimedia agregados: {media_count}")

        logger.info(
            f"   🚀 RUN_ID {run_id}: Enviando a GPT-4o-mini "
            f"({len(ads_with_media)} anuncios, {total_images} imágenes, "
            f"{total_video_frames} frames de video)..."
        )

        messages = [{"role": "user", "content": content}]

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=4096,
            temperature=0.5  # Balance precisión-creatividad para análisis
        )

        logger.info(f"   ✅ RUN_ID {run_id}: Respuesta recibida")

        analysis_text = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.info(
            f"   📊 RUN_ID {run_id}: Tokens: {tokens_used}, "
            f"Chars: {len(analysis_text)}"
        )

        # Construir respuesta JSON
        result = {
            'status': 'success',
            'run_id': run_id,
            'mode': 'local-only',
            'total_ads_analyzed': len(ads_with_media),
            'total_images': total_images,
            'total_video_frames': total_video_frames,
            'total_videos': total_videos,
            'tokens_used': tokens_used,
            'model': 'gpt-4o-mini',
            'analysis': analysis_text,
            'timestamp': datetime.now().isoformat(),
            'ads_details': [
                {
                    'ad_id': ad['ad_id'],
                    'media_count': len(ad['media']),
                    'images': sum(1 for m in ad['media'] if m['type'] == 'image'),
                    'video_frames': sum(1 for m in ad['media'] if m['type'] == 'video_frame')
                }
                for ad in ads_with_media
            ]
        }

        # Guardar JSON local
        logger.info(f"   💾 RUN_ID {run_id}: Guardando resultado...")
        reports_dir = base_dir / 'reports_json'
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_filename = f"{run_id}_local_analysis.json"
        report_path = reports_dir / report_filename

        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"   ✅ RUN_ID {run_id}: Guardado en {report_filename}")
        logger.info("="*80)
        logger.info(f"🎉 RUN_ID {run_id}: ANÁLISIS LOCAL COMPLETADO")
        logger.info("="*80)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ RUN_ID {run_id}: ERROR EN ANÁLISIS LOCAL")
        logger.error("="*80)
        logger.error(f"   🔴 Tipo: {type(e).__name__}")
        logger.error(f"   🔴 Mensaje: {str(e)}")
        logger.exception("   📋 Traceback:")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post(
    '/compare-campaigns',
    tags=["ai-analysis"],
    summary="Comparación de 2 campañas con análisis detallado de multimedia"
)
async def compare_campaigns(
    run_id_1: str,
    run_id_2: str,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Análisis comparativo de 2 campañas con OpenAI.

    Compara:
    - Rendimiento de imágenes vs videos
    - Métricas de ambas campañas
    - Información detallada de cada archivo multimedia
    - Análisis visual con OpenAI GPT-4o

    Args:
        run_id_1: ID de la primera campaña
        run_id_2: ID de la segunda campaña
        top_n: Anuncios a analizar por campaña (default: 10)

    Returns:
        JSON con análisis comparativo completo
    """
    logger.info("="*80)
    logger.info("🔀 ANÁLISIS COMPARATIVO DE CAMPAÑAS")
    logger.info("="*80)
    logger.info(f"📋 Campaña 1: {run_id_1}")
    logger.info(f"📋 Campaña 2: {run_id_2}")
    logger.info(f"📊 Top N por campaña: {top_n}")

    try:
        # PASO 1: Verificar OpenAI
        logger.info("\n📡 PASO 1/6: Verificando OpenAI...")
        from openai import OpenAI

        api_key = os.getenv("OPEN_API_KEY")
        if not api_key:
            raise HTTPException(503, "OPEN_API_KEY no configurada")

        openai_client = OpenAI(api_key=api_key)
        logger.info("   ✅ OpenAI configurado")

        # PASO 2: Procesar ambas campañas
        logger.info("\n📊 PASO 2/6: Procesando ambas campañas...")
        from pathlib import Path
        import csv
        import json as json_module
        from app.processors.facebook.analyze_dataset import analyze

        base_dir = get_facebook_saved_base()

        campaigns_data = []

        for idx, run_id in enumerate([run_id_1, run_id_2], 1):
            logger.info(f"\n   📂 Procesando Campaña {idx}: {run_id}")

            run_dir = base_dir / run_id
            if not run_dir.exists():
                raise HTTPException(404, f"Run ID {run_id} no encontrado")

            csv_path = run_dir / f"{run_id}.csv"
            if not csv_path.exists():
                raise HTTPException(404, f"CSV no encontrado para {run_id}")

            # Analizar dataset
            stats = analyze(csv_path)
            items = sorted(
                stats.values(),
                key=lambda x: x.get('score', 0),
                reverse=True
            )
            top_ads = [it.get('ad_id') for it in items[:top_n]]

            logger.info(
                f"      ✅ {len(stats)} anuncios, top {len(top_ads)} seleccionados")

            # Extraer metadatos del CSV
            csv_metadata = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ad_id = (
                        row.get('ad_archive_id') or
                        row.get('adArchiveID') or
                        row.get('id')
                    )
                    if ad_id in top_ads:
                        csv_metadata.append({
                            'ad_id': ad_id,
                            'page_name': row.get('page_name', 'N/A'),
                            'ad_creation_time': row.get('ad_creation_time', 'N/A'),
                            'ad_creative_bodies': row.get('ad_creative_bodies', 'N/A'),
                            'impressionsMin': row.get('impressionsMin', 'N/A'),
                            'impressionsMax': row.get('impressionsMax', 'N/A'),
                            'spendMin': row.get('spendMin', 'N/A'),
                            'spendMax': row.get('spendMax', 'N/A'),
                        })

            campaigns_data.append({
                'run_id': run_id,
                'run_dir': run_dir,
                'top_ads': top_ads,
                'metadata': csv_metadata
            })

        # PASO 3: Descargar y analizar multimedia
        logger.info("\n📥 PASO 3/6: Descargando multimedia de ambas campañas...")
        from app.processors.facebook.download_images_from_csv import (
            make_session,
            download_one,
            iter_csv_snapshot_rows,
            extract_urls_from_snapshot
        )
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import base64

        session = make_session()

        for campaign in campaigns_data:
            run_id = campaign['run_id']
            run_dir = campaign['run_dir']
            csv_path = run_dir / f"{run_id}.csv"
            media_dir = run_dir / 'media'
            media_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"   📥 Campaña {run_id}: Descargando multimedia...")

            downloaded = 0
            with ThreadPoolExecutor(max_workers=6) as ex:
                futures = []
                for row, snapshot in iter_csv_snapshot_rows(csv_path):
                    ad_id = (
                        row.get('ad_archive_id') or
                        row.get('ad_id') or
                        'unknown'
                    )
                    if ad_id not in campaign['top_ads']:
                        continue
                    if not snapshot:
                        continue
                    urls = extract_urls_from_snapshot(snapshot)
                    for u in urls[:10]:  # Max 10 archivos por anuncio
                        futures.append(
                            ex.submit(
                                download_one,
                                session,
                                u,
                                media_dir,
                                prefix=ad_id
                            )
                        )

                for fut in as_completed(futures):
                    url, path = fut.result()
                    if path:
                        downloaded += 1

            logger.info(f"      ✅ {downloaded} archivos descargados")
            campaign['downloaded_count'] = downloaded

        # PASO 4: Codificar multimedia y clasificar (imagen/video)
        logger.info("\n🖼️  PASO 4/6: Codificando y clasificando multimedia...")

        for campaign in campaigns_data:
            run_id = campaign['run_id']
            media_dir = campaign['run_dir'] / 'media'

            logger.info(f"   🔄 Campaña {run_id}: Procesando archivos...")

            media_files = []
            images_count = 0
            videos_count = 0

            for ad_id in campaign['top_ads']:
                matched = [
                    p for p in media_dir.iterdir()
                    if p.is_file() and p.name.startswith(str(ad_id))
                ]

                for file_path in matched[:10]:
                    file_ext = file_path.suffix.lower()
                    file_size = file_path.stat().st_size

                    # Clasificar tipo de archivo
                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        file_type = 'image'
                        images_count += 1

                        # Codificar imagen en base64
                        try:
                            with open(file_path, 'rb') as f:
                                img_data = f.read()
                                b64_str = base64.b64encode(
                                    img_data).decode('utf-8')

                                mime_type = 'image/jpeg'
                                if file_ext == '.png':
                                    mime_type = 'image/png'
                                elif file_ext == '.gif':
                                    mime_type = 'image/gif'
                                elif file_ext == '.webp':
                                    mime_type = 'image/webp'

                                media_files.append({
                                    'ad_id': ad_id,
                                    'filename': file_path.name,
                                    'type': file_type,
                                    'extension': file_ext,
                                    'size_bytes': file_size,
                                    'size_mb': round(file_size / (1024*1024), 2),
                                    'mime_type': mime_type,
                                    'base64': b64_str
                                })
                        except Exception as e:
                            logger.warning(
                                f"      ⚠️  Error con {file_path.name}: {e}")

                    elif file_ext in ['.mp4', '.mov', '.avi', '.webm']:
                        file_type = 'video'
                        videos_count += 1

                        # Para videos, guardar metadata pero NO codificar
                        media_files.append({
                            'ad_id': ad_id,
                            'filename': file_path.name,
                            'type': file_type,
                            'extension': file_ext,
                            'size_bytes': file_size,
                            'size_mb': round(file_size / (1024*1024), 2),
                            'local_path': str(file_path),
                            'base64': None  # Videos no se envían a OpenAI
                        })

            campaign['media_files'] = media_files
            campaign['images_count'] = images_count
            campaign['videos_count'] = videos_count

            logger.info(
                f"      ✅ {images_count} imágenes, {videos_count} videos"
            )

        # PASO 5: Preparar datos comparativos
        logger.info("\n📊 PASO 5/6: Preparando análisis comparativo...")

        # Cargar prompt
        env_prompt = os.getenv('PROMPT')
        if not env_prompt:
            prompt_file_name = os.getenv('PROMPT_FILE', 'prompt.txt')
            prompt_file_path = (
                Path(__file__).parent.parent.parent.parent.parent.parent /
                prompt_file_name
            )
            if prompt_file_path.exists():
                env_prompt = prompt_file_path.read_text(encoding='utf-8')
            else:
                env_prompt = DEFAULT_PROMPT

        # Construir texto comparativo con metadatos
        comparison_text = "\n\n**ANÁLISIS COMPARATIVO DE 2 CAMPAÑAS**\n\n"

        for idx, campaign in enumerate(campaigns_data, 1):
            comparison_text += f"**CAMPAÑA {idx} (RUN_ID: {campaign['run_id']})**\n\n"
            comparison_text += f"- Total anuncios analizados: {len(campaign['top_ads'])}\n"
            comparison_text += f"- Archivos multimedia: {len(campaign['media_files'])}\n"
            comparison_text += f"  - Imágenes: {campaign['images_count']}\n"
            comparison_text += f"  - Videos: {campaign['videos_count']}\n\n"

            comparison_text += "**Metadatos del CSV:**\n```json\n"
            comparison_text += json_module.dumps(
                campaign['metadata'],
                ensure_ascii=False,
                indent=2
            )
            comparison_text += "\n```\n\n"

            comparison_text += "**Detalle de archivos multimedia:**\n```json\n"
            # Info de archivos sin base64 (muy largo)
            files_info = [
                {
                    'ad_id': f['ad_id'],
                    'filename': f['filename'],
                    'type': f['type'],
                    'extension': f['extension'],
                    'size_mb': f['size_mb']
                }
                for f in campaign['media_files']
            ]
            comparison_text += json_module.dumps(
                files_info,
                ensure_ascii=False,
                indent=2
            )
            comparison_text += "\n```\n\n"

        # Construir mensaje con prompt + comparación + solo imágenes
        content = [
            {
                "type": "text",
                "text": env_prompt + comparison_text
            }
        ]

        # Agregar SOLO imágenes (videos no soportados en base64)
        total_images_sent = 0
        for campaign in campaigns_data:
            for media in campaign['media_files']:
                if media['type'] == 'image' and media.get('base64'):
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:{media['mime_type']};"
                                f"base64,{media['base64']}"
                            )
                        }
                    })
                    total_images_sent += 1

        logger.info(
            f"   📤 Enviando {total_images_sent} imágenes a OpenAI "
            f"(videos solo como metadata)"
        )

        # PASO 6: Analizar con OpenAI
        logger.info("\n🤖 PASO 6/6: Analizando con OpenAI...")

        messages = [{"role": "user", "content": content}]

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=4096,
            temperature=0.5  # Balance precisión-creatividad para análisis comparativo
        )

        analysis_text = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.info(
            f"   ✅ Análisis completado ({tokens_used} tokens, "
            f"{len(analysis_text)} chars)"
        )

        # Construir respuesta
        result = {
            'status': 'success',
            'mode': 'campaign-comparison',
            'campaigns': [
                {
                    'run_id': c['run_id'],
                    'ads_analyzed': len(c['top_ads']),
                    'total_media_files': len(c['media_files']),
                    'images_count': c['images_count'],
                    'videos_count': c['videos_count'],
                    'metadata': c['metadata'],
                    'media_details': [
                        {
                            'ad_id': m['ad_id'],
                            'filename': m['filename'],
                            'type': m['type'],
                            'size_mb': m['size_mb']
                        }
                        for m in c['media_files']
                    ]
                }
                for c in campaigns_data
            ],
            'tokens_used': tokens_used,
            'model': 'gpt-4o',
            'analysis': analysis_text,
            'timestamp': datetime.now().isoformat()
        }

        # Guardar reporte
        logger.info("   💾 Guardando reporte comparativo...")
        reports_dir = base_dir / 'reports_json'
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_filename = f"comparison_{run_id_1}_vs_{run_id_2}.json"
        report_path = reports_dir / report_filename

        with open(report_path, 'w', encoding='utf-8') as f:
            json_module.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"   ✅ Guardado en {report_filename}")
        logger.info("="*80)
        logger.info("🎉 ANÁLISIS COMPARATIVO COMPLETADO")
        logger.info("="*80)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("="*80)
        logger.error("❌ ERROR EN ANÁLISIS COMPARATIVO")
        logger.error("="*80)
        logger.error(f"   🔴 Tipo: {type(e).__name__}")
        logger.error(f"   🔴 Mensaje: {str(e)}")
        logger.exception("   📋 Traceback:")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post(
    '/generate-latex-report',
    tags=["ai-analysis"],
    summary="Genera reporte LaTeX desde análisis JSON"
)
async def generate_latex_report(run_id: str) -> Dict[str, Any]:
    """
    Genera código LaTeX profesional desde un análisis JSON ya guardado.

    Este endpoint:
    1. Lee el archivo JSON de análisis del run_id
    2. Usa OpenAI con prompt_latex.txt para generar LaTeX
    3. Guarda el archivo .tex
    4. Devuelve el código LaTeX completo

    El usuario puede compilar el .tex con:
    - MikTeX (Windows)
    - TeX Live (Linux/Mac)
    - Overleaf (online)

    Args:
        run_id: ID de la campaña con análisis JSON guardado

    Returns:
        JSON con código LaTeX y ruta del archivo
    """
    logger.info("="*80)
    logger.info("📄 GENERACIÓN DE REPORTE LATEX")
    logger.info("="*80)
    logger.info(f"📋 Run ID: {run_id}")

    try:
        # PASO 1: Verificar OpenAI
        logger.info("\n📡 PASO 1/4: Verificando OpenAI...")
        from openai import OpenAI

        api_key = os.getenv("OPEN_API_KEY")
        if not api_key:
            raise HTTPException(503, "OPEN_API_KEY no configurada")

        openai_client = OpenAI(api_key=api_key)
        logger.info("   ✅ OpenAI configurado")

        # PASO 2: Leer análisis JSON guardado
        logger.info("\n📂 PASO 2/4: Buscando análisis JSON...")
        from pathlib import Path
        import json as json_module

        base_dir = get_facebook_saved_base()
        reports_dir = base_dir / 'reports_json'

        # Buscar archivo JSON del análisis
        json_path = reports_dir / f"{run_id}_local_analysis.json"

        if not json_path.exists():
            raise HTTPException(
                404,
                f"No se encontró análisis JSON para run_id: {run_id}. "
                f"Ejecuta primero /analyze-local-only"
            )

        logger.info(f"   ✅ JSON encontrado: {json_path.name}")

        # Leer JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            analysis_json = json_module.load(f)

        logger.info(
            f"   📊 Anuncios analizados: {analysis_json.get('total_ads_analyzed', 0)}")
        logger.info(f"   🖼️  Imágenes: {analysis_json.get('total_images', 0)}")

        # PASO 3: Cargar prompt LaTeX
        logger.info("\n📝 PASO 3/4: Cargando prompt LaTeX...")

        prompt_file_name = os.getenv('PROMPT_LATEX_FILE', 'prompt_latex.txt')
        # Obtener directorio api_service/ (7 niveles arriba desde analysis.py)
        # analysis.py -> routes -> facebook -> apify -> routes -> api -> app -> api_service
        current_file = Path(__file__)
        api_service_dir = current_file.parent.parent.parent.parent.parent.parent.parent
        prompt_file_path = api_service_dir / prompt_file_name

        logger.info(f"   🔍 Buscando prompt en: {prompt_file_path}")

        if not prompt_file_path.exists():
            raise HTTPException(
                500,
                f"Archivo de prompt LaTeX no encontrado: {prompt_file_name}. "
                f"Ruta buscada: {prompt_file_path}"
            )

        latex_prompt = prompt_file_path.read_text(encoding='utf-8')
        logger.info(f"   ✅ Prompt cargado: {prompt_file_name}")

        # PASO 4: Generar LaTeX con OpenAI
        logger.info("\n🤖 PASO 4/4: Generando código LaTeX con OpenAI...")

        # Limpiar y parsear el campo 'analysis' si está como string
        if 'analysis' in analysis_json and isinstance(analysis_json['analysis'], str):
            try:
                # Remover markdown code blocks
                analysis_str = analysis_json['analysis']
                if '```json' in analysis_str:
                    analysis_str = analysis_str.split(
                        '```json')[1].split('```')[0]
                elif '```' in analysis_str:
                    analysis_str = analysis_str.split('```')[1].split('```')[0]

                analysis_str = analysis_str.strip()
                parsed_analysis = json_module.loads(analysis_str)
                analysis_json['parsed_analysis'] = parsed_analysis
                logger.info("   ✅ Análisis parseado correctamente")
            except Exception as e:
                logger.warning(
                    f"   ⚠️ No se pudo parsear 'analysis': {str(e)}")

        # Preparar mensaje: Prompt + JSON de análisis
        message_content = f"{latex_prompt}\n\n"
        message_content += "**DATOS DE ENTRADA - Análisis en JSON:**\n\n"
        message_content += "```json\n"
        message_content += json_module.dumps(analysis_json,
                                             ensure_ascii=False, indent=2)
        message_content += "\n```\n\n"
        message_content += "Genera el código LaTeX completo y profesional basándote en este análisis."

        # Enviar a OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en LaTeX. Generas código LaTeX profesional y compilable."
                },
                {
                    "role": "user",
                    "content": message_content
                }
            ],
            max_tokens=4096,
            temperature=0.2  # Muy baja para código LaTeX preciso y compilable
        )

        latex_code = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.info(
            f"   ✅ LaTeX generado ({tokens_used} tokens, {len(latex_code)} chars)")

        # Limpiar código LaTeX (remover markdown si existe)
        if latex_code.startswith("```latex"):
            latex_code = latex_code.replace("```latex", "", 1)
        if latex_code.startswith("```"):
            latex_code = latex_code.replace("```", "", 1)
        if latex_code.endswith("```"):
            latex_code = latex_code[:-3]
        latex_code = latex_code.strip()

        # Guardar archivo .tex
        logger.info("   💾 Guardando archivo .tex...")
        reports_dir.mkdir(parents=True, exist_ok=True)

        tex_filename = f"{run_id}_report.tex"
        tex_path = reports_dir / tex_filename

        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(latex_code)

        logger.info(f"   ✅ Guardado: {tex_filename}")
        logger.info("\n" + "="*80)
        logger.info("🎉 CÓDIGO LATEX GENERADO EXITOSAMENTE")
        logger.info("="*80)
        logger.info(f"📄 Archivo: {tex_path}")
        logger.info("\n💡 Para compilar a PDF:")
        logger.info(f"   cd {reports_dir}")
        logger.info(f"   pdflatex {tex_filename}")
        logger.info("="*80)

        return {
            'status': 'success',
            'run_id': run_id,
            'tex_file': str(tex_path),
            'tex_filename': tex_filename,
            'latex_code': latex_code,
            'tokens_used': tokens_used,
            'model': 'gpt-4o',
            'timestamp': datetime.now().isoformat(),
            'compile_instructions': {
                'windows_miktex': f'pdflatex {tex_filename}',
                'linux_texlive': f'pdflatex {tex_filename}',
                'online_overleaf': 'Subir archivo .tex a Overleaf y compilar'
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ RUN_ID {run_id}: ERROR EN GENERACIÓN LATEX")
        logger.error("="*80)
        logger.error(f"   🔴 Tipo: {type(e).__name__}")
        logger.error(f"   🔴 Mensaje: {str(e)}")
        logger.exception("   📋 Traceback:")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post(
    '/compile-latex-to-pdf',
    tags=["ai-analysis"],
    summary="Compila archivo LaTeX a PDF"
)
async def compile_latex_endpoint(run_id: str) -> Dict[str, Any]:
    """
    Compila un archivo .tex existente a PDF usando pdflatex.

    Este endpoint:
    1. Busca el archivo .tex del run_id
    2. Ejecuta pdflatex para compilar a PDF
    3. Limpia archivos auxiliares (.aux, .log, etc)
    4. Guarda el PDF en el mismo directorio

    Requisitos:
    - pdflatex instalado (MiKTeX en Windows, TeX Live en Linux/Mac)

    Args:
        run_id: ID de la campaña con archivo .tex generado

    Returns:
        JSON con ruta del PDF y resultado de compilación
    """
    import json as json_module

    logger.info("="*80)
    logger.info("📄 COMPILACIÓN LATEX A PDF")
    logger.info("="*80)
    logger.info(f"📋 Run ID: {run_id}")

    try:
        # PASO 1: Validar directorio
        logger.info("\n📁 PASO 1/3: Validando directorios...")

        # Usar la función helper para obtener la ruta base correcta
        base_dir = get_facebook_saved_base()
        reports_dir = base_dir / 'reports_json'

        if not reports_dir.exists():
            raise HTTPException(
                404,
                f"Directorio no encontrado: {reports_dir}. "
                f"Ejecuta primero /generate-latex-report"
            )

        logger.info(f"   ✅ Directorio: {reports_dir}")

        # PASO 2: Buscar archivo .tex
        logger.info("\n📄 PASO 2/3: Buscando archivo .tex...")

        tex_filename = f"{run_id}_report.tex"
        tex_path = reports_dir / tex_filename

        if not tex_path.exists():
            raise HTTPException(
                404,
                f"Archivo .tex no encontrado: {tex_filename}. "
                f"Ejecuta primero /generate-latex-report"
            )

        logger.info(f"   ✅ Archivo encontrado: {tex_filename}")
        logger.info(f"   📊 Tamaño: {tex_path.stat().st_size} bytes")

        # PASO 3: Compilar a PDF
        logger.info("\n🔨 PASO 3/3: Compilando LaTeX a PDF...")

        pdf_result = compile_latex_to_pdf(
            tex_path=tex_path,
            output_dir=reports_dir
        )

        if pdf_result['success']:
            pdf_filename = pdf_result['pdf_filename']
            pdf_path = reports_dir / pdf_filename

            logger.info(f"   ✅ PDF generado: {pdf_filename}")
            logger.info(f"   📊 Tamaño: {pdf_path.stat().st_size} bytes")
            logger.info("\n" + "="*80)
            logger.info("🎉 PDF GENERADO EXITOSAMENTE")
            logger.info("="*80)
            logger.info(f"📄 Archivo: {pdf_path}")

            return {
                'status': 'success',
                'run_id': run_id,
                'pdf_file': str(pdf_path),
                'pdf_filename': pdf_filename,
                'pdf_size_bytes': pdf_path.stat().st_size,
                'tex_file': str(tex_path),
                'timestamp': datetime.now().isoformat()
            }
        else:
            error_msg = pdf_result['error']
            logger.error("\n" + "="*80)
            logger.error("❌ ERROR EN COMPILACIÓN PDF")
            logger.error("="*80)
            logger.error(f"   🔴 Error: {error_msg}")

            raise HTTPException(
                500,
                f"Error al compilar PDF: {error_msg}. "
                f"Asegúrate de tener pdflatex instalado (MiKTeX o TeX Live)"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ RUN_ID {run_id}: ERROR EN COMPILACIÓN")
        logger.error("="*80)
        logger.error(f"   🔴 Tipo: {type(e).__name__}")
        logger.error(f"   🔴 Mensaje: {str(e)}")
        logger.exception("   📋 Traceback:")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post(
    '/generate-pdf-report',
    tags=["ai-analysis"],
    summary="Genera reporte PDF directamente desde análisis JSON"
)
async def generate_pdf_report(run_id: str) -> Dict[str, Any]:
    """
    Genera PDF profesional directamente desde análisis JSON usando ReportLab.

    NO requiere pdflatex instalado - generación 100% Python.

    Este endpoint:
    1. Lee el archivo JSON de análisis del run_id
    2. Usa ReportLab para generar PDF directamente
    3. Guarda el PDF en el mismo directorio
    4. Devuelve información del PDF generado

    Args:
        run_id: ID de la campaña con análisis JSON guardado

    Returns:
        JSON con ruta del PDF y detalles
    """
    import json as json_module

    logger.info("="*80)
    logger.info("📄 GENERACIÓN DE PDF CON REPORTLAB")
    logger.info("="*80)
    logger.info(f"📋 Run ID: {run_id}")

    try:
        # PASO 1: Buscar análisis JSON
        logger.info("\n📂 PASO 1/2: Buscando análisis JSON...")

        base_dir = get_facebook_saved_base()
        reports_dir = base_dir / 'reports_json'

        json_path = reports_dir / f"{run_id}_local_analysis.json"

        if not json_path.exists():
            raise HTTPException(
                404,
                f"No se encontró análisis JSON para run_id: {run_id}. "
                f"Ejecuta primero /analyze-local-only"
            )

        logger.info(f"   ✅ JSON encontrado: {json_path.name}")

        # Leer JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            analysis_json = json_module.load(f)

        logger.info(
            f"   📊 Anuncios: {analysis_json.get('total_ads_analyzed', 0)}")

        # PASO 2: Generar PDF
        logger.info("\n📄 PASO 2/2: Generando PDF con ReportLab...")

        pdf_filename = f"{run_id}_report.pdf"
        pdf_path = reports_dir / pdf_filename

        result = create_pdf_from_analysis(
            analysis_json=analysis_json,
            output_path=pdf_path,
            run_id=run_id
        )

        if result['success']:
            pdf_size = pdf_path.stat().st_size

            logger.info(f"   ✅ PDF generado: {pdf_filename}")
            logger.info(f"   📊 Tamaño: {pdf_size:,} bytes")
            logger.info("\n" + "="*80)
            logger.info("🎉 PDF GENERADO EXITOSAMENTE")
            logger.info("="*80)
            logger.info(f"📄 Archivo: {pdf_path}")

            return {
                'status': 'success',
                'run_id': run_id,
                'pdf_file': str(pdf_path),
                'pdf_filename': pdf_filename,
                'pdf_size_bytes': pdf_size,
                'generator': 'reportlab',
                'timestamp': datetime.now().isoformat()
            }
        else:
            logger.error("\n" + "="*80)
            logger.error("❌ ERROR EN GENERACIÓN PDF")
            logger.error("="*80)
            logger.error(f"   🔴 Error: {result['error']}")

            raise HTTPException(
                500, f"Error al generar PDF: {result['error']}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ RUN_ID {run_id}: ERROR EN GENERACIÓN PDF")
        logger.error("="*80)
        logger.error(f"   🔴 Tipo: {type(e).__name__}")
        logger.error(f"   🔴 Mensaje: {str(e)}")
        logger.exception("   📋 Traceback:")
        raise HTTPException(500, f"Error: {str(e)}")
