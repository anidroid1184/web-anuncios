"""
Endpoint mejorado analyze-local-only con ngrok
Reemplaza la codificación base64 por URLs públicas vía ngrok
"""

# PASO 4 MEJORADO: Exponer archivos con ngrok
import json
import random
logger.info("\n🌐 PASO 4/5: Exponiendo archivos con ngrok...")

# 1. Procesar videos: extraer frames
frames_dir = run_dir / 'video_frames'
frames_dir.mkdir(parents=True, exist_ok=True)

all_videos = list(media_dir.glob('*.mp4')) + list(media_dir.glob('*.mov'))
logger.info(f"   📹 Videos detectados: {len(all_videos)}")

total_frames_extracted = 0
for video_path in all_videos[:5]:  # Máx 5 videos
    try:
        logger.info(f"   🎥 Extrayendo frames: {video_path.name}")
        frames = extract_frames_from_video(video_path, num_frames=3)

        for i, frame_data in enumerate(frames):
            frame_filename = f"{video_path.stem}_frame{i}.jpg"
            frame_path = frames_dir / frame_filename

            import base64
            frame_bytes = base64.b64decode(frame_data['base64'])
            frame_path.write_bytes(frame_bytes)
            total_frames_extracted += 1

        logger.info(f"      ✅ {len(frames)} frames extraídos")
    except Exception as e:
        logger.warning(f"      ⚠️  Error: {e}")

logger.info(f"   ✅ Total frames extraídos: {total_frames_extracted}")

# 2. Iniciar servidor HTTP para media_dir + frames_dir
port = random.randint(8100, 8999)


class QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


# Cambiar al run_dir para servir media/ y video_frames/
os.chdir(run_dir)
httpd = socketserver.TCPServer(("", port), QuietHTTPHandler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
logger.info(f"   🌐 Servidor HTTP iniciado en puerto {port}")

# 3. Crear túnel ngrok
tunnel = ngrok.connect(port)
public_url = tunnel.public_url
logger.info(f"   ✅ Túnel ngrok: {public_url}")

# 4. Construir lista de archivos con URLs públicas
media_urls = []
total_images = 0
total_videos = 0

# Imágenes del media_dir
for ad_id in top_ads:
    ad_files = [
        p for p in media_dir.iterdir()
        if p.is_file() and str(ad_id) in p.stem and
        p.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ]

    for file_path in ad_files[:3]:  # Máx 3 por anuncio
        media_urls.append({
            'ad_id': ad_id,
            'type': 'image',
            'filename': file_path.name,
            'url': f"{public_url}/media/{file_path.name}"
        })
        total_images += 1

# Frames de videos
for frame_file in frames_dir.iterdir():
    if frame_file.suffix.lower() == '.jpg':
        media_urls.append({
            'ad_id': 'video_frame',
            'type': 'video_frame',
            'filename': frame_file.name,
            'url': f"{public_url}/video_frames/{frame_file.name}"
        })
        total_videos += 1

logger.info(f"   ✅ URLs generadas: {len(media_urls)} archivos")
logger.info(f"      - Imágenes: {total_images}")
logger.info(f"      - Frames de video: {total_videos}")

# PASO 5: Analizar con OpenAI usando URLs públicas
logger.info("\n🤖 PASO 5/5: Analizando con OpenAI...")

# Cargar prompt
env_prompt = os.getenv('PROMPT', DEFAULT_PROMPT)
logger.info(f"   📝 Prompt: {len(env_prompt)} caracteres")

# Construir contenido con URLs
content = [
    {
        "type": "text",
        "text": f"{env_prompt}\n\nAnaliza las siguientes {len(media_urls)} imágenes:"
    }
]

for media in media_urls:
    content.append({
        "type": "image_url",
        "image_url": {
            "url": media['url'],
            "detail": "auto"
        }
    })

logger.info(f"   🖼️  Total elementos multimedia: {len(media_urls)}")
logger.info(f"   🚀 Enviando a GPT-4o-mini...")

messages = [{"role": "user", "content": content}]

response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    max_tokens=4096,
    temperature=0.5
)

analysis_text = response.choices[0].message.content or ""
tokens_used = response.usage.total_tokens if response.usage else 0

logger.info(f"   ✅ Respuesta recibida")
logger.info(f"   📊 Tokens: {tokens_used}, Chars: {len(analysis_text)}")

# Construir respuesta JSON
result = {
    'status': 'success',
    'run_id': run_id,
    'mode': 'local-with-ngrok',
    'total_files_analyzed': len(media_urls),
    'total_images': total_images,
    'total_video_frames': total_videos,
    'tokens_used': tokens_used,
    'model': 'gpt-4o-mini',
    'ngrok_tunnel': public_url,
    'analysis': analysis_text,
    'timestamp': datetime.now().isoformat(),
    'media_urls': media_urls
}

# Guardar JSON
reports_dir = base_dir / 'reports_json'
reports_dir.mkdir(parents=True, exist_ok=True)

report_filename = f"{run_id}_ngrok_analysis.json"
report_path = reports_dir / report_filename

with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

logger.info(f"   ✅ Guardado: {report_filename}")
logger.info("="*80)
logger.info("🎉 ANÁLISIS COMPLETADO CON NGROK")
logger.info("="*80)

return result
