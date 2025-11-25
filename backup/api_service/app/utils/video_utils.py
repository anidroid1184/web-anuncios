"""
Utilidades para procesamiento de videos
Extrae frames de videos para análisis con IA
"""
import cv2
import base64
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def extract_frames_from_video(
    video_path: Path,
    num_frames: int = 10,
    output_dir: Optional[Path] = None
) -> List[Dict[str, any]]:
    """
    Extrae frames uniformemente distribuidos de un video.

    Args:
        video_path: Ruta al archivo de video
        num_frames: Número de frames a extraer (default: 10)
        output_dir: Directorio opcional para guardar frames como imágenes

    Returns:
        Lista de diccionarios con información de cada frame:
        {
            'frame_number': int,
            'timestamp': float (segundos),
            'base64': str (imagen codificada en base64),
            'file_path': Optional[Path] (si se guardó en disco)
        }
    """
    frames_data = []

    try:
        # Abrir video
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            logger.error(f"No se pudo abrir el video: {video_path}")
            return frames_data

        # Obtener información del video
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0

        logger.info(
            f"Video: {video_path.name} - "
            f"{total_frames} frames, {fps:.2f} FPS, {duration:.2f}s"
        )

        # Calcular frames a extraer (distribuidos uniformemente)
        if total_frames < num_frames:
            num_frames = total_frames

        frame_indices = [
            int(i * total_frames / num_frames)
            for i in range(num_frames)
        ]

        # Crear directorio de salida si se especificó
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

        # Extraer frames
        for idx, frame_idx in enumerate(frame_indices):
            # Posicionar en el frame deseado
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

            ret, frame = cap.read()
            if not ret:
                logger.warning(f"No se pudo leer frame {frame_idx}")
                continue

            # Calcular timestamp
            timestamp = frame_idx / fps if fps > 0 else 0

            # Codificar frame en base64 (formato JPEG)
            _, buffer = cv2.imencode('.jpg', frame)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')

            frame_info = {
                'frame_number': frame_idx,
                'timestamp': round(timestamp, 2),
                'base64': frame_b64,
                'width': frame.shape[1],
                'height': frame.shape[0]
            }

            # Guardar frame como imagen si se especificó directorio
            if output_dir:
                frame_filename = (
                    f"{video_path.stem}_frame_{idx:03d}_"
                    f"t{timestamp:.2f}s.jpg"
                )
                frame_path = output_dir / frame_filename
                cv2.imwrite(str(frame_path), frame)
                frame_info['file_path'] = frame_path

            frames_data.append(frame_info)

        cap.release()

        logger.info(
            f"✅ Extraídos {len(frames_data)} frames de {video_path.name}"
        )

    except Exception as e:
        logger.error(f"Error extrayendo frames de {video_path}: {e}")
        logger.exception(e)

    return frames_data


def get_video_metadata(video_path: Path) -> Dict[str, any]:
    """
    Obtiene metadatos de un video sin extraer frames.

    Args:
        video_path: Ruta al archivo de video

    Returns:
        Diccionario con metadatos del video
    """
    metadata = {
        'file_path': str(video_path),
        'file_name': video_path.name,
        'file_size_mb': round(video_path.stat().st_size / (1024*1024), 2),
        'extension': video_path.suffix,
        'exists': video_path.exists()
    }

    try:
        cap = cv2.VideoCapture(str(video_path))

        if cap.isOpened():
            metadata.update({
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': round(cap.get(cv2.CAP_PROP_FPS), 2),
                'total_frames': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'duration_seconds': round(
                    int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) /
                    cap.get(cv2.CAP_PROP_FPS),
                    2
                ) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0,
                'codec': int(cap.get(cv2.CAP_PROP_FOURCC))
            })
            cap.release()
        else:
            logger.warning(
                f"No se pudo abrir video para metadatos: {video_path}")

    except Exception as e:
        logger.error(f"Error obteniendo metadatos de {video_path}: {e}")

    return metadata


def batch_extract_frames(
    video_paths: List[Path],
    num_frames: int = 10,
    output_base_dir: Optional[Path] = None
) -> Dict[str, List[Dict]]:
    """
    Extrae frames de múltiples videos en paralelo.

    Args:
        video_paths: Lista de rutas a videos
        num_frames: Frames por video
        output_base_dir: Directorio base para guardar frames

    Returns:
        Diccionario con video_name -> lista de frames
    """
    results = {}

    for video_path in video_paths:
        output_dir = None
        if output_base_dir:
            output_dir = output_base_dir / video_path.stem

        frames = extract_frames_from_video(
            video_path,
            num_frames=num_frames,
            output_dir=output_dir
        )

        if frames:
            results[video_path.name] = frames

    return results
