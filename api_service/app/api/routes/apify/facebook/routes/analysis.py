"""
AI Analysis Routes - Análisis optimizado con Base64 (SIN GCS, SIN NGROK)
Endpoints para análisis con OpenAI usando codificación Base64 en memoria
"""
import threading
import socketserver
import http.server
import json
import re
from json_repair import repair_json
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any
import os
from pyngrok import ngrok
from datetime import datetime
import logging
from pathlib import Path

from ..utils.config import get_facebook_saved_base

# Configurar logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

router = APIRouter(tags=["Facebook"])


def start_local_file_server(directory, port=8000):
    """Inicia servidor HTTP local para servir archivos"""
    handler = http.server.SimpleHTTPRequestHandler
    os.chdir(directory)
    httpd = socketserver.TCPServer(("", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


@router.post(
    '/expose-single-file',
    tags=["ai-analysis"],
    summary="Expone archivo y analiza con OpenAI (ngrok + prompt personalizado)"
)
async def expose_single_file(
    file: UploadFile = File(...),
    prompt: str = "Analiza esta imagen publicitaria y describe todos los elementos visuales, texto, y estrategia de marketing que observes."
) -> Dict[str, Any]:
    """
    Expone un archivo con URL pública via ngrok y lo analiza con OpenAI Vision.

    Este endpoint:
    1. Guarda el archivo subido temporalmente
    2. Inicia un servidor HTTP local
    3. Crea un túnel ngrok para URL pública
    4. Envía la URL a OpenAI Vision con el prompt
    5. Retorna análisis completo + URL pública

    Args:
        file: Archivo a analizar (imagen/video - selector de archivo)
        prompt: Prompt personalizado para el análisis

    Returns:
        JSON con análisis de OpenAI y URL pública del archivo
    """
    filename = file.filename
    logger.info(f"🔍 Analizando archivo: {filename}")

    try:
        # Crear directorio temporal
        temp_dir = Path("temp_ngrok_files") / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Guardar archivo subido
        file_path = temp_dir / filename

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        file_size = file_path.stat().st_size
        logger.info(f"   ✅ Archivo guardado: {file_path} ({file_size} bytes)")

        # Iniciar servidor HTTP en puerto libre
        import random
        port = random.randint(8100, 8999)

        class QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Silenciar logs del servidor

        os.chdir(temp_dir)
        httpd = socketserver.TCPServer(("", port), QuietHTTPHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        logger.info(f"   🌐 Servidor HTTP iniciado en puerto {port}")

        # Crear túnel ngrok
        tunnel = ngrok.connect(port)
        public_url = tunnel.public_url
        file_url = f"{public_url}/{filename}"

        logger.info(f"   ✅ Túnel ngrok creado: {file_url}")

        # PASO 2: Analizar con OpenAI Vision
        logger.info(f"\n🤖 Analizando imagen con OpenAI Vision...")
        logger.info(f"   - Prompt: {prompt[:100]}...")

        try:
            from openai import OpenAI

            # Obtener API key (buscar ambos nombres para compatibilidad)
            api_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPEN_API_KEY')
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY no configurada en .env"
                )

            openai_client = OpenAI(api_key=api_key)
            logger.info("   ✅ Cliente OpenAI inicializado")

            # Llamar a OpenAI Vision con la URL pública
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": file_url}
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )

            analysis_result = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            logger.info(f"   ✅ Análisis completado")
            logger.info(f"   - Tokens usados: {tokens_used}")
            logger.info(f"   - Longitud: {len(analysis_result)} chars")

            return {
                "status": "success",
                "filename": filename,
                "public_url": file_url,
                "tunnel_url": public_url,
                "analysis": analysis_result,
                "prompt_used": prompt,
                "model": "gpt-4o-mini",
                "tokens_used": tokens_used,
                "local_path": str(file_path),
                "file_size_bytes": file_size,
                "file_extension": file_path.suffix,
                "timestamp": datetime.now().isoformat(),
                "note": "Análisis completado. URL pública activa."
            }

        except Exception as openai_error:
            logger.error(f"   ❌ Error OpenAI: {str(openai_error)}")
            return {
                "status": "partial_success",
                "filename": filename,
                "public_url": file_url,
                "tunnel_url": public_url,
                "error": f"Análisis falló: {str(openai_error)}",
                "file_size_bytes": file_size,
                "note": "URL creada pero análisis falló"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


@router.post(
    '/analyze-local-only',
    tags=["ai-analysis"],
    summary="Análisis con OpenAI desde run_id local (Base64 optimizado, sin GCS)"
)
async def analyze_local_only(
    run_id: str,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Análisis completo con OpenAI usando Base64.

    FLUJO SIMPLE:
    1. Seleccionar anuncios del CSV
    2. Descargar imágenes → Base64
    3. Extraer frames de videos → Base64
    4. Enviar TODO a OpenAI

    Args:
        run_id: ID del run con datos locales
        top_n: Número de anuncios a analizar (default: 10)
    """
    logger.info("="*80)
    logger.info("🚀 ANÁLISIS CON BASE64")
    logger.info("="*80)
    logger.info(f"📋 RUN_ID: {run_id}")
    logger.info(f"📊 Top N: {top_n}")

    try:
        # PASO 1: OpenAI
        logger.info("\n📡 PASO 1: Configurando OpenAI...")
        from openai import AsyncOpenAI
        import base64
        from io import BytesIO
        from PIL import Image

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

        # PASO 3: Seleccionar anuncios
        logger.info("\n📊 PASO 3: Seleccionando anuncios...")
        import pandas as pd
        df = pd.read_csv(csv_path)

        logger.info(f"   📄 CSV cargado: {len(df)} filas")

        media_data = {}
        count = 0
        errores = 0

        for idx, row in df.iterrows():
            if count >= top_n:
                break

            ad_id = str(row.get('ad_archive_id')
                        or row.get('ad_id') or f'ad_{idx}')
            snapshot_str = row.get('snapshot', '{}')

            # NUEVA LÓGICA: Extraer URLs directamente del snapshot sin parsear JSON
            img_urls = []
            vid_urls = []

            # Convertir snapshot a string y buscar URLs con regex
            if pd.notna(snapshot_str):
                snapshot_text = str(snapshot_str)

                # Buscar URLs de imágenes (cualquier URL que parezca imagen)
                img_patterns = [
                    r'https?://[^\s"\',}]+\.(?:jpg|jpeg|png|webp)',
                    r'"(?:original_image_url|resized_image_url)":\s*"([^"]+)"',
                    r"'(?:original_image_url|resized_image_url)':\s*'([^']+)'"
                ]

                for pattern in img_patterns:
                    matches = re.findall(pattern, snapshot_text, re.IGNORECASE)
                    for match in matches[:3]:  # Máximo 3 imágenes
                        url = match if isinstance(match, str) else match[0]
                        if url and url.startswith('http'):
                            img_urls.append(url)
                            if len(img_urls) >= 3:
                                break
                    if img_urls:
                        break

                # Buscar URLs de videos
                vid_patterns = [
                    r'https?://[^\s"\',}]+\.(?:mp4|mov|avi)',
                    r'"(?:video_hd_url|video_sd_url)":\s*"([^"]+)"',
                    r"'(?:video_hd_url|video_sd_url)':\s*'([^']+)'"
                ]

                for pattern in vid_patterns:
                    matches = re.findall(pattern, snapshot_text, re.IGNORECASE)
                    if matches:
                        url = matches[0] if isinstance(
                            matches[0], str) else matches[0][0]
                        if url and url.startswith('http'):
                            vid_urls.append(url)
                            break

            # Si encontramos multimedia, agregar
            if img_urls or vid_urls:
                media_data[ad_id] = {
                    'images': img_urls,
                    'videos': vid_urls
                }
                count += 1
                logger.info(
                    f"   ✓ {ad_id}: {len(img_urls)} imgs, {len(vid_urls)} vids")
            else:
                errores += 1

        logger.info(f"   ✅ {len(media_data)} anuncios con multimedia")
        logger.info(f"   ⚠️  {errores} anuncios sin multimedia")

        if len(media_data) == 0:
            raise HTTPException(404, "No se encontró multimedia en el dataset")

        # PASO 4: Buscar archivos YA DESCARGADOS en storage
        logger.info("\n📦 PASO 4: Buscando archivos descargados...")

        # Directorio correcto: run_dir contiene media/ y opcionalmente video_frames/
        media_dir = run_dir / "media"
        video_frames_dir = run_dir / "video_frames"

        logger.info(f"   📁 Media: {media_dir}")

        if not media_dir.exists():
            raise HTTPException(
                404, f"Directorio media no existe: {media_dir}")

        # PASO 4.1: Extraer frames de videos encontrados en media/
        logger.info("\n🎬 Extrayendo frames de videos...")
        
        # Buscar archivos de video en media/
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        video_files = [
            f for f in media_dir.iterdir()
            if f.is_file() and f.suffix.lower() in video_extensions
        ]
        
        if video_files:
            logger.info(f"   📹 {len(video_files)} videos encontrados")
            
            # Crear directorio de frames si no existe
            video_frames_dir.mkdir(exist_ok=True)
            
            try:
                import cv2
                
                for video_path in video_files:
                    try:
                        logger.info(f"   🔄 Procesando: {video_path.name}")
                        
                        cap = cv2.VideoCapture(str(video_path))
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        
                        # Extraer 3 frames: inicio, medio, fin
                        frames_to_extract = [
                            0,  # Primer frame
                            frame_count // 2,  # Frame del medio
                            frame_count - 1  # Último frame
                        ]
                        
                        # Nombre base del video (sin extensión)
                        base_name = video_path.stem
                        
                        extracted = 0
                        for i, frame_num in enumerate(frames_to_extract):
                            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                            ret, frame = cap.read()
                            
                            if ret:
                                # Guardar frame
                                frame_filename = (
                                    f"{base_name}_frame{i}.jpg"
                                )
                                frame_path = video_frames_dir / frame_filename
                                cv2.imwrite(str(frame_path), frame)
                                extracted += 1
                        
                        cap.release()
                        logger.info(
                            f"      ✅ {extracted} frames extraídos"
                        )
                        
                    except Exception as e:
                        logger.error(
                            f"      ❌ Error con {video_path.name}: {e}"
                        )
                        continue
                
            except ImportError:
                logger.warning(
                    "   ⚠️  OpenCV no disponible, "
                    "no se pueden extraer frames"
                )
        else:
            logger.info("   ℹ️  No hay videos para procesar")

        # video_frames es opcional
        has_video_frames = video_frames_dir.exists()
        if has_video_frames:
            logger.info(f"   📁 Frames: {video_frames_dir}")
        else:
            logger.info(
                "   ℹ️  No hay directorio video_frames (anuncios sin videos)")

        # Cargar prompt desde archivo configurado
        prompt_file = os.getenv("PROMPT_FILE", "prompt_simple.txt")
        prompt_path = Path("prompts") / prompt_file

        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read().strip()
            logger.info(f"   📄 Prompt cargado desde: {prompt_file}")
        else:
            # Fallback si no existe el archivo
            prompt_template = "Analiza estos anuncios de Facebook. Describe estrategia visual, colores, mensajes y elementos clave."
            logger.warning(
                f"   ⚠️  Archivo {prompt_file} no encontrado, usando prompt por defecto")

        # Preparar información del dataset para el prompt
        dataset_info = f"""
INFORMACIÓN DEL DATASET:
- Run ID: {run_id}
- Total de anuncios en CSV: {len(df)}
- Anuncios con multimedia: {len(media_data)}
- IDs de anuncios seleccionados: {', '.join(media_data.keys())}

INSTRUCCIÓN CRÍTICA: Debes retornar ÚNICAMENTE un objeto JSON válido y completo.
No agregues texto adicional antes o después del JSON.
El JSON debe seguir EXACTAMENTE la estructura solicitada en el prompt.
Genera un análisis COMPLETO Y DETALLADO para cada anuncio.
"""

        content_blocks = []
        content_blocks.append({
            "type": "text",
            "text": dataset_info + "\n\n" + prompt_template
        })

        total_imgs = 0
        total_video_frames = 0

        for ad_id in media_data.keys():
            logger.info(f"   📋 Anuncio {ad_id}")
            
            # Separar imágenes estáticas de frames de video
            static_images = []
            video_frames = []

            # Buscar en media/ - imágenes estáticas
            for img_file in media_dir.iterdir():
                if img_file.is_file() and img_file.name.startswith(str(ad_id)):
                    if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                        static_images.append(img_file)

            # Buscar frames de video solo si existe el directorio
            if has_video_frames:
                for frame_file in video_frames_dir.iterdir():
                    if frame_file.is_file() and frame_file.name.startswith(str(ad_id)):
                        if frame_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                            video_frames.append(frame_file)

            logger.info(
                f"      📁 {len(static_images)} imgs estáticas, "
                f"{len(video_frames)} frames de video"
            )

            # Agregar header del anuncio con tipo de contenido
            ad_header = f"\n{'='*60}\nANUNCIO ID: {ad_id}\n"
            if static_images:
                ad_header += f"- IMÁGENES ESTÁTICAS: {len(static_images)}\n"
            if video_frames:
                ad_header += f"- VIDEO (frames extraídos): {len(video_frames)}\n"
            ad_header += f"{'='*60}\n"
            
            content_blocks.append({
                "type": "text",
                "text": ad_header
            })

            # Procesar TODAS las imágenes estáticas
            if static_images:
                content_blocks.append({
                    "type": "text",
                    "text": "\n📷 IMÁGENES ESTÁTICAS:\n"
                })
                
                for img_path in static_images:
                    try:
                        with Image.open(img_path) as img:
                            if img.mode in ('RGBA', 'P'):
                                img = img.convert('RGB')
                            if max(img.size) > 800:
                                img.thumbnail(
                                    (800, 800),
                                    Image.Resampling.LANCZOS
                                )
                            buffered = BytesIO()
                            img.save(
                                buffered,
                                format="JPEG",
                                quality=85,
                                optimize=True
                            )
                            b64 = base64.b64encode(
                                buffered.getvalue()
                            ).decode('utf-8')

                            content_blocks.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64}",
                                    "detail": "low"
                                }
                            })
                            total_imgs += 1
                            logger.info(f"      ✓ IMG: {img_path.name}")
                    except Exception as e:
                        logger.error(
                            f"      ✗ Error en {img_path.name}: {e}"
                        )

            # Procesar TODOS los frames de video
            if video_frames:
                content_blocks.append({
                    "type": "text",
                    "text": (
                        "\n🎥 FRAMES DE VIDEO "
                        "(extraídos del anuncio en video):\n"
                    )
                })
                
                for frame_path in video_frames:
                    try:
                        with Image.open(frame_path) as img:
                            if img.mode in ('RGBA', 'P'):
                                img = img.convert('RGB')
                            if max(img.size) > 800:
                                img.thumbnail(
                                    (800, 800),
                                    Image.Resampling.LANCZOS
                                )
                            buffered = BytesIO()
                            img.save(
                                buffered,
                                format="JPEG",
                                quality=85,
                                optimize=True
                            )
                            b64 = base64.b64encode(
                                buffered.getvalue()
                            ).decode('utf-8')

                            content_blocks.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64}",
                                    "detail": "low"
                                }
                            })
                            total_video_frames += 1
                            logger.info(
                                f"      ✓ VIDEO FRAME: {frame_path.name}"
                            )
                    except Exception as e:
                        logger.error(
                            f"      ✗ Error en {frame_path.name}: {e}"
                        )

        # PASO 5: Enviar a OpenAI
        logger.info("\n🚀 PASO 5: Enviando a OpenAI...")
        logger.info(
            f"   📊 Total: {total_imgs} imágenes estáticas + "
            f"{total_video_frames} frames de video"
        )

        total_assets = total_imgs + total_video_frames
        if total_assets == 0:
            raise HTTPException(400, "No se procesó ninguna multimedia")

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content_blocks}],
            max_tokens=16000  # Permitir respuestas mucho más largas
        )

        analysis = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        logger.info(f"   ✅ Completado - {tokens_used} tokens")

        return {
            "status": "success",
            "run_id": run_id,
            "analyzed_ads": len(media_data),
            "total_images_processed": total_imgs,
            "total_video_frames_processed": total_video_frames,
            "total_assets": total_assets,
            "analysis": analysis,
            "tokens_used": tokens_used,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ Error: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post(
    '/analyze-and-generate-pdf',
    tags=["ai-analysis"],
    summary="Análisis con OpenAI + Generación de PDF (Base64 optimizado)"
)
async def analyze_and_generate_pdf(
    run_id: str,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Análisis completo con OpenAI + generación de PDF profesional.

    Flujo:
    1. Analiza anuncios con OpenAI (igual que analyze-local-only)
    2. Parsea el JSON de respuesta
    3. Genera un PDF profesional con ReportLab
    4. Retorna la ruta del PDF generado

    Args:
        run_id: ID del run con datos locales
        top_n: Número de anuncios a analizar (default: 10)
    """
    logger.info("="*80)
    logger.info("🚀 ANÁLISIS + GENERACIÓN PDF")
    logger.info("="*80)

    try:
        # Ejecutar análisis (reutilizar lógica de analyze-local-only)
        analysis_result = await analyze_local_only(run_id, top_n)

        # Verificar que el análisis fue exitoso
        if analysis_result.get("status") != "success":
            raise HTTPException(500, "Análisis falló")

        analysis_text = analysis_result.get("analysis", "")

        logger.info("\n📄 Procesando respuesta de OpenAI...")

        # Buscar JSON en la respuesta (puede estar envuelto en markdown)
        # Primero intentar extraer de bloques ```json
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        json_match = re.search(json_pattern, analysis_text, re.DOTALL)

        if not json_match:
            # Si no hay bloque markdown, buscar JSON directamente
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)

        if json_match:
            if json_match.lastindex:  # Tiene grupo de captura
                json_str = json_match.group(1)
            else:
                json_str = json_match.group(0)

            # Intentar parsear JSON con json-repair
            try:
                # Primero intento con json estándar
                analysis_data = json.loads(json_str)
                logger.info("   ✅ JSON parseado correctamente")
            except json.JSONDecodeError as e:
                logger.warning(
                    f"   ⚠️  JSON malformado (pos {e.pos}), "
                    f"reparando con json-repair..."
                )

                try:
                    # Usar json-repair para reparar JSON automáticamente
                    # repair_json retorna directamente el objeto Python
                    repaired_data = repair_json(json_str)

                    # Asegurar que sea un diccionario
                    if isinstance(repaired_data, dict):
                        analysis_data = repaired_data
                        logger.info("   ✅ JSON reparado exitosamente")
                    else:
                        raise ValueError(
                            f"repair_json retornó {type(repaired_data)}"
                        )
                except Exception as repair_error:
                    logger.error(
                        f"   ❌ json-repair falló: {str(repair_error)}"
                    )
                    # Crear estructura básica
                    overview_text = (
                        analysis_text[:300]
                        if len(analysis_text) > 300
                        else analysis_text
                    )
                    analysis_data = {
                        "metadata": {
                            "campaign_name": f"Análisis {run_id}",
                            "total_ads_analyzed": top_n
                        },
                        "executive_summary": {
                            "overview": overview_text,
                            "key_findings": (
                                "Análisis parcial - JSON incompleto"
                            ),
                            "strategic_implications": (
                                "Se recomienda reducir el número de "
                                "anuncios o simplificar el prompt"
                            )
                        },
                        "assets_analysis": [],
                        "global_conclusions": {
                            "summary": (
                                "Análisis generado pero respuesta "
                                "incompleta de OpenAI"
                            )
                        }
                    }
        else:
            # Si no hay JSON, crear estructura básica
            logger.warning(
                "   ⚠️  No se encontró JSON, usando estructura básica")
            overview_text = (
                analysis_text[:300]
                if len(analysis_text) > 300
                else analysis_text
            )
            analysis_data = {
                "metadata": {
                    "campaign_name": f"Análisis {run_id}",
                    "total_ads_analyzed": top_n
                },
                "executive_summary": {
                    "overview": overview_text,
                    "key_findings": (
                        "Respuesta de OpenAI sin formato JSON"
                    ),
                    "strategic_implications": "Texto plano convertido"
                },
                "assets_analysis": [],
                "global_conclusions": {
                    "summary": analysis_text
                }
            }

        # Guardar JSON y Markdown
        logger.info("\n💾 Guardando resultados...")
        
        # Crear directorio de reportes si no existe
        reports_dir = get_facebook_saved_base() / "reports"
        reports_dir.mkdir(exist_ok=True)

        # Guardar JSON
        json_filename = f"{run_id}_analysis.json"
        json_path = reports_dir / json_filename
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"   ✅ JSON guardado: {json_path}")

        # Guardar respuesta completa en Markdown estructurado
        md_filename = f"{run_id}_analysis.md"
        md_path = reports_dir / md_filename
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Análisis de Campaña: {run_id}\n\n")
            fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"**Fecha:** {fecha}\n\n")
            ads = analysis_result.get('analyzed_ads', 0)
            f.write(f"**Anuncios analizados:** {ads}\n\n")
            imgs = analysis_result.get('total_images_processed', 0)
            frames = analysis_result.get('total_video_frames_processed', 0)
            f.write(f"**Imágenes estáticas:** {imgs}\n\n")
            f.write(f"**Frames de video:** {frames}\n\n")
            tokens = analysis_result.get('tokens_used', 0)
            f.write(f"**Tokens usados:** {tokens}\n\n")
            f.write("---\n\n")
            
            # Extraer y destacar sección de comparación si existe
            if isinstance(analysis_data, dict):
                comp = analysis_data.get('comparative_analysis')
                if comp:
                    f.write("## 🏆 ANÁLISIS COMPARATIVO\n\n")
                    
                    # Ganador
                    winner = comp.get('winner', {})
                    if winner:
                        f.write(f"### 🥇 GANADOR: {winner.get('asset_id')}\n\n")
                        f.write(f"**Razones:** {winner.get('reasons')}\n\n")
                        strengths = winner.get('key_strengths', [])
                        if strengths:
                            f.write("**Fortalezas clave:**\n")
                            for s in strengths:
                                f.write(f"- {s}\n")
                            f.write("\n")
                    
                    # Runner up
                    runner = comp.get('runner_up', {})
                    if runner:
                        runner_id = runner.get('asset_id')
                        f.write(f"### 🥈 SEGUNDO LUGAR: {runner_id}\n\n")
                        f.write(f"{runner.get('reasons')}\n\n")
                    
                    # Tabla de ranking
                    ranking = comp.get('ranking_table', [])
                    if ranking:
                        f.write("### 📊 TABLA DE RANKING\n\n")
                        f.write(
                            "| Rank | Anuncio ID | Score | "
                            "Mejor Atributo |\n"
                        )
                        f.write(
                            "|------|------------|-------|"
                            "----------------|\n"
                        )
                        for r in ranking:
                            rank = r.get('rank', '')
                            aid = r.get('asset_id', '')
                            score = r.get('overall_score', '')
                            attr = r.get('best_attribute', '')
                            f.write(f"| {rank} | {aid} | {score} | {attr} |\n")
                        f.write("\n")
                    
                    f.write("---\n\n")
            
            f.write("## 📄 Respuesta Completa de OpenAI\n\n")
            f.write(analysis_text)
        
        logger.info(f"   ✅ Markdown guardado: {md_path}")

        return {
            "status": "success",
            "run_id": run_id,
            "analyzed_ads": analysis_result.get("analyzed_ads", 0),
            "total_images_processed": analysis_result.get(
                "total_images_processed", 0
            ),
            "tokens_used": analysis_result.get("tokens_used", 0),
            "json_path": str(json_path),
            "json_filename": json_filename,
            "markdown_path": str(md_path),
            "markdown_filename": md_filename,
            "analysis_data": analysis_data,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"   ❌ Error parseando JSON: {str(e)}")
        raise HTTPException(
            500, f"Error parseando respuesta de OpenAI: {str(e)}")
    except Exception as e:
        logger.error(f"   ❌ Error: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post(
    '/json-to-pdf',
    tags=["ai-analysis"],
    summary="Convierte JSON de análisis a PDF usando OpenAI"
)
async def json_to_pdf(run_id: str) -> Dict[str, Any]:
    """
    Toma el JSON guardado de un análisis previo y genera un PDF
    profesional usando OpenAI para formatear y estructurar el contenido.
    
    Args:
        run_id: ID del run con el JSON de análisis guardado
    
    Returns:
        Información del PDF generado
    """
    logger.info("="*80)
    logger.info(f"📄 GENERANDO PDF DESDE JSON: {run_id}")
    logger.info("="*80)
    
    try:
        # Buscar archivo JSON
        reports_dir = get_facebook_saved_base() / "reports"
        json_path = reports_dir / f"{run_id}_analysis.json"
        
        if not json_path.exists():
            raise HTTPException(
                404,
                f"No se encontró análisis para run_id: {run_id}"
            )
        
        # Cargar JSON
        logger.info(f"\n📂 Cargando JSON: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        logger.info("   ✅ JSON cargado correctamente")
        
        # Usar OpenAI para estructurar contenido en formato Markdown
        logger.info("\n🤖 Usando OpenAI para formatear reporte...")
        
        from openai import AsyncOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(500, "OPENAI_API_KEY no configurada")
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Prompt para formatear el JSON en Markdown estructurado
        format_prompt = f"""
Eres un editor profesional de reportes de marketing.
Toma este análisis en JSON y conviértelo en un reporte Markdown
profesional, bien estructurado y fácil de leer.

Estructura requerida:
1. Título principal y metadata
2. Resumen ejecutivo
3. Análisis por activo (cada imagen analizada)
4. Análisis cruzado
5. Conclusiones globales
6. Hoja de ruta estratégica

Usa formato Markdown con:
- Headers apropiados (# ## ###)
- Listas y viñetas
- Tablas para scores
- Énfasis en puntos clave (**bold**)
- Separadores visuales (---)

JSON:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Genera SOLO el Markdown, sin explicaciones adicionales.
"""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": format_prompt
                }
            ],
            max_tokens=8000,
            temperature=0.3
        )
        
        markdown_content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        logger.info(f"   ✅ Markdown generado ({tokens_used} tokens)")
        
        # Guardar Markdown formateado
        md_formatted_path = reports_dir / f"{run_id}_formatted.md"
        with open(md_formatted_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"   ✅ Markdown guardado: {md_formatted_path}")
        
        # Convertir Markdown a PDF usando markdown-pdf
        logger.info("\n📄 Convirtiendo a PDF...")
        
        try:
            from markdown_pdf import MarkdownPdf, Section
            
            pdf_filename = f"{run_id}_report.pdf"
            pdf_path = reports_dir / pdf_filename
            
            pdf = MarkdownPdf()
            pdf.add_section(Section(markdown_content))
            pdf.save(str(pdf_path))
            
            logger.info(f"   ✅ PDF generado: {pdf_path}")
            
            return {
                "status": "success",
                "run_id": run_id,
                "json_path": str(json_path),
                "markdown_path": str(md_formatted_path),
                "pdf_path": str(pdf_path),
                "pdf_filename": pdf_filename,
                "tokens_used": tokens_used,
                "timestamp": datetime.now().isoformat()
            }
            
        except ImportError:
            # Si no está markdown-pdf, intentar con ReportLab directamente
            logger.warning(
                "   ⚠️  markdown-pdf no disponible, "
                "usando conversión simplificada"
            )
            
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer
            )
            from reportlab.lib.units import inch
            
            pdf_filename = f"{run_id}_report.pdf"
            pdf_path = reports_dir / pdf_filename
            
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            styles = getSampleStyleSheet()
            story = []
            
            # Convertir Markdown a párrafos simples
            for line in markdown_content.split('\n'):
                if line.strip():
                    # Remover sintaxis markdown básica
                    clean_line = line.replace('**', '').replace('##', '')
                    clean_line = clean_line.replace('#', '')
                    story.append(Paragraph(clean_line, styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))
            
            doc.build(story)
            
            logger.info(f"   ✅ PDF simple generado: {pdf_path}")
            
            return {
                "status": "success",
                "run_id": run_id,
                "json_path": str(json_path),
                "markdown_path": str(md_formatted_path),
                "pdf_path": str(pdf_path),
                "pdf_filename": pdf_filename,
                "tokens_used": tokens_used,
                "method": "simplified",
                "timestamp": datetime.now().isoformat()
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Error generando PDF: {str(e)}")


@router.post(
    '/upload-local-files',
    tags=["ai-analysis"],
    summary="Sube múltiples archivos y expone con ngrok"
)
async def upload_local_files(files: list[UploadFile] = File(...)):
    """
    Sube archivos locales y los expone con URLs públicas via ngrok.
    """
    temp_dir = "temp_uploaded_files"
    os.makedirs(temp_dir, exist_ok=True)
    saved_files = []

    for file in files:
        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        saved_files.append(file_path)

    # Iniciar servidor local
    port = 8000
    httpd, thread = start_local_file_server(temp_dir, port)

    # Exponer con ngrok
    public_url = ngrok.connect(port)

    # Construir URLs públicas
    public_file_urls = [
        f"{public_url}/{os.path.basename(f)}" for f in saved_files
    ]

    return {
        "status": "success",
        "public_url": public_url,
        "file_urls": public_file_urls,
        "files_count": len(saved_files),
        "note": "URLs activas mientras el servidor esté corriendo"
    }
