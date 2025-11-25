import os
import json
import logging
import threading
import socketserver
import http.server
from pathlib import Path
from typing import Dict, Any, List, Tuple
from fastapi import HTTPException
from pyngrok import ngrok

logger = logging.getLogger(__name__)

def load_all_ads_from_run(run_id: str, run_dir: Path) -> List[Dict[str, Any]]:
    """
    Loads ALL ads data from a local run directory.
    """
    # Try to load from prepared_data.json first
    prepared_json_path = run_dir / "prepared_data.json"
    
    if prepared_json_path.exists():
        logger.info(f"Loading ads from {prepared_json_path}")
        with open(prepared_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Get ALL ads, not just top
            all_ads = data.get('all_ads', data.get('top_ads', []))
            if all_ads:
                logger.info(f"Loaded {len(all_ads)} ads from prepared_data.json")
                return all_ads
    
    # Fallback: Parse CSV and get ALL rows
    csv_path = run_dir / f"{run_id}.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"No data found for run_id: {run_id}")
    
    logger.info(f"Parsing CSV: {csv_path}")
    import pandas as pd
    
    df = pd.read_csv(csv_path)
    logger.info(f"Found {len(df)} total ads in CSV")
    
    # Convert ALL rows to list of dicts
    all_ads = []
    for idx, row in df.iterrows():
        ad_dict = {
            'ad_id': str(row.get('ad_archive_id') or row.get('ad_id') or f'ad_{idx}'),
            'spend': row.get('spend', 0),
            'impressions': row.get('impressions', 0),
            'reach': row.get('reach', 0),
            'snapshot': str(row.get('snapshot', '{}'))
        }
        all_ads.append(ad_dict)
    
    logger.info(f"Extracted {len(all_ads)} ads from CSV")
    return all_ads


def expose_media_via_ngrok(run_dir: Path) -> Tuple[str, Any]:
    """
    Exposes the media directory via ngrok and returns the public URL.
    
    Returns:
        Tuple of (public_url, httpd_server)
    """
    media_dir = run_dir / "media"
    
    if not media_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Media directory not found: {media_dir}"
        )
    
    logger.info(f"📁 Exposing media directory: {media_dir}")
    
    # Start HTTP server
    import random
    port = random.randint(8100, 8999)
    
    class QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Silenciar logs
    
    os.chdir(media_dir)
    httpd = socketserver.TCPServer(("", port), QuietHTTPHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    
    logger.info(f"🌐 HTTP server started on port {port}")
    
    # Create ngrok tunnel
    tunnel = ngrok.connect(port)
    public_url = tunnel.public_url
    
    logger.info(f"✅ Ngrok tunnel created: {public_url}")
    
    return public_url, httpd


def prepare_media_urls_for_analysis(run_dir: Path, public_url: str) -> List[Dict[str, Any]]:
    """
    Prepares a list of all media files with their public URLs.
    
    Returns:
        List of dicts with file info and public URLs
    """
    media_dir = run_dir / "media"
    media_files = []
    
    # Get all image and video files
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    
    for file_path in media_dir.iterdir():
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in image_extensions or ext in video_extensions:
                media_type = 'image' if ext in image_extensions else 'video'
                file_url = f"{public_url}/{file_path.name}"
                
                media_files.append({
                    'filename': file_path.name,
                    'type': media_type,
                    'url': file_url,
                    'local_path': str(file_path)
                })
    
    logger.info(f"📊 Prepared {len(media_files)} media files for analysis")
    return media_files

