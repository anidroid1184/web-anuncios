"""
Async Media Encoder
Codificación asíncrona masiva de imágenes y frames
"""

import asyncio
import base64
from pathlib import Path
from typing import List, Dict, Optional
import logging
import aiofiles
from .image_optimizer import ImageOptimizer

logger = logging.getLogger(__name__)


class AsyncMediaEncoder:
    """
    Codificador asíncrono de multimedia con optimización
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        max_size: int = 1024,
        quality: int = 85
    ):
        """
        Args:
            max_concurrent: Máximo de archivos procesados simultáneamente
            max_size: Tamaño máximo de imagen (px)
            quality: Calidad JPEG
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.optimizer = ImageOptimizer(
            max_width=max_size,
            max_height=max_size,
            quality=quality
        )

    async def encode_single_file(
        self,
        file_path: Path,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Codifica un archivo individual de forma asíncrona

        Returns:
            {
                'file_path': str,
                'base64': str,
                'metadata': dict,
                'status': 'ok' | 'error',
                'error': str (si aplica)
            }
        """
        async with self.semaphore:
            try:
                # Leer archivo de forma asíncrona
                async with aiofiles.open(file_path, 'rb') as f:
                    image_bytes = await f.read()

                # Optimizar y codificar (síncrono pero rápido)
                base64_str, opt_metadata = await asyncio.to_thread(
                    self.optimizer.optimize_and_encode,
                    image_bytes
                )

                # Combinar metadata
                result_metadata = {
                    'filename': file_path.name,
                    'size_kb': len(image_bytes) / 1024,
                    **opt_metadata
                }

                if metadata:
                    result_metadata.update(metadata)

                return {
                    'file_path': str(file_path),
                    'base64': base64_str,
                    'metadata': result_metadata,
                    'status': 'ok'
                }

            except Exception as e:
                logger.error(f"Error codificando {file_path}: {e}")
                return {
                    'file_path': str(file_path),
                    'error': str(e),
                    'status': 'error'
                }

    async def encode_batch(
        self,
        file_paths: List[Path],
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Codifica múltiples archivos en paralelo

        Args:
            file_paths: Lista de rutas a procesar
            progress_callback: Función callback(completed, total)

        Returns:
            Lista de resultados
        """
        tasks = []

        for file_path in file_paths:
            task = self.encode_single_file(file_path)
            tasks.append(task)

        results = []
        completed = 0

        # Procesar con callback de progreso
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1

            if progress_callback:
                progress_callback(completed, len(file_paths))

        return results

    async def encode_directory(
        self,
        directory: Path,
        extensions: tuple = ('.jpg', '.jpeg', '.png'),
        recursive: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, List[Dict]]:
        """
        Codifica todos los archivos de un directorio

        Returns:
            {
                'successful': [...],
                'failed': [...],
                'total': int,
                'success_count': int,
                'error_count': int
            }
        """
        # Buscar archivos
        if recursive:
            files = [
                p for p in directory.rglob('*')
                if p.is_file() and p.suffix.lower() in extensions
            ]
        else:
            files = [
                p for p in directory.iterdir()
                if p.is_file() and p.suffix.lower() in extensions
            ]

        logger.info(f"Encontrados {len(files)} archivos en {directory}")

        # Codificar en lote
        results = await self.encode_batch(files, progress_callback)

        # Separar éxitos y errores
        successful = [r for r in results if r['status'] == 'ok']
        failed = [r for r in results if r['status'] == 'error']

        return {
            'successful': successful,
            'failed': failed,
            'total': len(results),
            'success_count': len(successful),
            'error_count': len(failed)
        }


async def encode_images_async(
    image_paths: List[Path],
    max_concurrent: int = 10,
    max_size: int = 1024
) -> List[Dict]:
    """
    Helper function: codifica lista de imágenes de forma asíncrona

    Args:
        image_paths: Lista de rutas
        max_concurrent: Concurrencia máxima
        max_size: Tamaño máximo

    Returns:
        Lista de resultados codificados
    """
    encoder = AsyncMediaEncoder(max_concurrent, max_size)
    return await encoder.encode_batch(image_paths)
