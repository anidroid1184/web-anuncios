"""
Frame Extractor - Extrae frames de videos desde URLs
"""

import base64
import tempfile
import requests
from pathlib import Path
from typing import List, Dict, Optional
import logging

from app.utils.video_utils import extract_frames_from_video

logger = logging.getLogger(__name__)


class VideoFrameExtractor:
    """
    Extrae frames de videos descargándolos temporalmente
    """

    def __init__(self, num_frames: int = 3):
        """
        Args:
            num_frames: Número de frames a extraer por video
        """
        self.num_frames = num_frames
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download_video_temp(self, video_url: str) -> Optional[Path]:
        """
        Descarga video temporalmente

        Args:
            video_url: URL del video

        Returns:
            Path al archivo temporal o None si falla
        """
        try:
            logger.debug(f"Descargando video: {video_url[:60]}...")
            response = self.session.get(video_url, timeout=30, stream=True)
            response.raise_for_status()

            # Crear archivo temporal
            suffix = '.mp4'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                temp_path = Path(tmp_file.name)

            logger.debug(
                f"Video descargado: {temp_path.stat().st_size / 1024:.1f} KB")
            return temp_path

        except Exception as e:
            logger.error(f"Error descargando video: {e}")
            return None

    def extract_frames(self, video_path: Path) -> List[Dict[str, str]]:
        """
        Extrae frames de un video

        Args:
            video_path: Path al archivo de video

        Returns:
            Lista de frames con base64 y metadata
        """
        try:
            frames = extract_frames_from_video(
                video_path, num_frames=self.num_frames)
            return frames
        except Exception as e:
            logger.error(f"Error extrayendo frames: {e}")
            return []

    def process_video_url(
        self,
        video_url: str,
        ad_id: str,
        save_dir: Optional[Path] = None
    ) -> List[Dict[str, any]]:
        """
        Procesa un video: descarga temporal -> extrae frames -> opcionalmente guarda

        Args:
            video_url: URL del video
            ad_id: ID del anuncio (para nombrar frames)
            save_dir: Directorio donde guardar frames (opcional)

        Returns:
            Lista de frames procesados con metadata
        """
        temp_video = None
        try:
            # Descargar temporalmente
            temp_video = self.download_video_temp(video_url)
            if not temp_video:
                return []

            # Extraer frames
            frames = self.extract_frames(temp_video)
            if not frames:
                return []

            processed_frames = []

            # Procesar cada frame
            for idx, frame_data in enumerate(frames):
                frame_info = {
                    'ad_id': ad_id,
                    'frame_index': idx,
                    'base64': frame_data['base64'],
                    'timestamp': frame_data.get('timestamp', 0),
                    'source': 'video',
                    'original_url': video_url
                }

                # Guardar en disco si se especifica directorio
                if save_dir:
                    save_dir.mkdir(parents=True, exist_ok=True)
                    frame_filename = f"{ad_id}_frame{idx}.jpg"
                    frame_path = save_dir / frame_filename

                    # Decodificar y guardar
                    frame_bytes = base64.b64decode(frame_data['base64'])
                    frame_path.write_bytes(frame_bytes)

                    frame_info['path'] = str(frame_path)
                    frame_info['filename'] = frame_filename

                    logger.debug(f"Frame guardado: {frame_filename}")

                processed_frames.append(frame_info)

            return processed_frames

        except Exception as e:
            logger.error(f"Error procesando video {video_url[:60]}: {e}")
            return []

        finally:
            # Limpiar archivo temporal
            if temp_video and temp_video.exists():
                try:
                    temp_video.unlink()
                    logger.debug("Archivo temporal eliminado")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar temporal: {e}")

    def process_multiple_videos(
        self,
        video_urls: List[str],
        ad_id: str,
        save_dir: Optional[Path] = None
    ) -> List[Dict[str, any]]:
        """
        Procesa múltiples videos de un anuncio

        Args:
            video_urls: Lista de URLs de videos
            ad_id: ID del anuncio
            save_dir: Directorio donde guardar frames

        Returns:
            Lista con todos los frames extraídos
        """
        all_frames = []

        for video_idx, video_url in enumerate(video_urls):
            logger.info(f"   🎥 Video {video_idx + 1}/{len(video_urls)}")

            frames = self.process_video_url(
                video_url=video_url,
                ad_id=f"{ad_id}_{video_idx}",
                save_dir=save_dir
            )

            all_frames.extend(frames)
            logger.info(f"      ✅ {len(frames)} frames extraídos")

        return all_frames


def extract_frames_from_url(
    video_url: str,
    ad_id: str,
    num_frames: int = 3,
    save_dir: Optional[Path] = None
) -> List[Dict[str, any]]:
    """
    Función helper para extraer frames de una URL de video

    Args:
        video_url: URL del video
        ad_id: ID del anuncio
        num_frames: Número de frames a extraer
        save_dir: Directorio donde guardar (opcional)

    Returns:
        Lista de frames procesados
    """
    extractor = VideoFrameExtractor(num_frames=num_frames)
    return extractor.process_video_url(video_url, ad_id, save_dir)
