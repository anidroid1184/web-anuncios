"""
Image Optimizer
Redimensiona y optimiza imágenes para OpenAI Vision
"""

import base64
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


class ImageOptimizer:
    """
    Optimiza imágenes para Vision API:
    - Redimensiona automáticamente
    - Convierte a RGB
    - Comprime sin perder calidad visible
    """

    def __init__(
        self,
        max_width: int = 1024,
        max_height: int = 1024,
        quality: int = 85
    ):
        """
        Args:
            max_width: Ancho máximo en píxeles
            max_height: Alto máximo en píxeles
            quality: Calidad JPEG (1-100)
        """
        self.max_width = max_width
        self.max_height = max_height
        self.quality = quality

    def optimize_image_bytes(
        self,
        image_bytes: bytes,
        format: str = 'JPEG'
    ) -> Tuple[bytes, dict]:
        """
        Optimiza bytes de imagen

        Returns:
            (bytes_optimizados, metadata)
        """
        try:
            # Abrir imagen
            img = Image.open(io.BytesIO(image_bytes))

            # Info original
            original_size = len(image_bytes)
            original_dims = img.size

            # Convertir a RGB si es necesario
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()
                                 [-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Redimensionar si es necesario
            if img.width > self.max_width or img.height > self.max_height:
                img.thumbnail((self.max_width, self.max_height),
                              Image.Resampling.LANCZOS)

            # Comprimir
            output = io.BytesIO()
            img.save(output, format=format,
                     quality=self.quality, optimize=True)
            optimized_bytes = output.getvalue()

            metadata = {
                'original_size': original_size,
                'optimized_size': len(optimized_bytes),
                'original_dimensions': original_dims,
                'final_dimensions': img.size,
                'compression_ratio': original_size / len(optimized_bytes) if optimized_bytes else 1,
                'format': format
            }

            return optimized_bytes, metadata

        except Exception as e:
            logger.error(f"Error optimizando imagen: {e}")
            # Retornar original si falla
            return image_bytes, {
                'error': str(e),
                'original_size': len(image_bytes)
            }

    def optimize_and_encode(
        self,
        image_bytes: bytes,
        format: str = 'JPEG'
    ) -> Tuple[str, dict]:
        """
        Optimiza y codifica en base64

        Returns:
            (base64_string, metadata)
        """
        optimized_bytes, metadata = self.optimize_image_bytes(
            image_bytes, format)
        base64_str = base64.b64encode(optimized_bytes).decode('utf-8')

        metadata['base64_size'] = len(base64_str)

        return base64_str, metadata


def optimize_image(
    image_path: Path,
    max_size: int = 1024,
    quality: int = 85
) -> Tuple[str, dict]:
    """
    Helper function: optimiza y codifica imagen desde archivo

    Args:
        image_path: Ruta a la imagen
        max_size: Tamaño máximo (ancho/alto)
        quality: Calidad JPEG

    Returns:
        (base64_string, metadata)
    """
    optimizer = ImageOptimizer(
        max_width=max_size, max_height=max_size, quality=quality)

    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    return optimizer.optimize_and_encode(image_bytes)
