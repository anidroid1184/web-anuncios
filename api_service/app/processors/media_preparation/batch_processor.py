"""
Batch Media Processor
Procesador de alto nivel para preparar lotes grandes de multimedia
"""

import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Optional
import logging
from tqdm.asyncio import tqdm as async_tqdm

from .async_encoder import AsyncMediaEncoder
from .image_optimizer import ImageOptimizer

logger = logging.getLogger(__name__)


class BatchMediaProcessor:
    """
    Procesador para conjuntos grandes de multimedia
    Combina optimización, codificación y organización por anuncios
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        max_image_size: int = 1024,
        quality: int = 85,
        detail_level: str = 'low'
    ):
        """
        Args:
            max_concurrent: Máximo de archivos en paralelo
            max_image_size: Tamaño máximo de imagen
            quality: Calidad JPEG (1-100)
            detail_level: 'low' | 'high' para OpenAI Vision
        """
        self.encoder = AsyncMediaEncoder(
            max_concurrent, max_image_size, quality
        )
        self.optimizer = ImageOptimizer(
            max_width=max_image_size,
            max_height=max_image_size,
            quality=quality
        )
        self.detail_level = detail_level
        self.stats = {
            'total_processed': 0,
            'total_errors': 0,
            'total_size_original': 0,
            'total_size_optimized': 0
        }

    async def process_ad_images(
        self,
        ad_id: str,
        image_paths: List[Path],
        max_images: int = 5
    ) -> Dict:
        """
        Procesa imágenes de un anuncio específico

        Returns:
            {
                'ad_id': str,
                'images': [...],
                'count': int,
                'errors': [...]
            }
        """
        # Limitar número de imágenes
        selected_paths = image_paths[:max_images]

        results = await self.encoder.encode_batch(selected_paths)

        images = []
        errors = []

        for result in results:
            if result['status'] == 'ok':
                images.append({
                    'ad_id': ad_id,
                    'type': 'image',
                    'source': 'original',
                    'base64': result['base64'],
                    'media_type': 'image/jpeg',
                    'filename': result['metadata']['filename'],
                    'size_kb': result['metadata'].get('optimized_size', 0) / 1024,
                    'detail': self.detail_level
                })

                # Actualizar stats
                self.stats['total_processed'] += 1
                self.stats['total_size_original'] += result['metadata'].get(
                    'original_size', 0)
                self.stats['total_size_optimized'] += result['metadata'].get(
                    'optimized_size', 0)
            else:
                errors.append({
                    'file': result['file_path'],
                    'error': result['error']
                })
                self.stats['total_errors'] += 1

        return {
            'ad_id': ad_id,
            'images': images,
            'count': len(images),
            'errors': errors
        }

    async def process_ad_frames(
        self,
        ad_id: str,
        frame_paths: List[Path],
        max_frames: int = 10
    ) -> Dict:
        """
        Procesa frames de video de un anuncio

        Returns:
            {
                'ad_id': str,
                'frames': [...],
                'count': int,
                'errors': [...]
            }
        """
        selected_paths = frame_paths[:max_frames]

        results = await self.encoder.encode_batch(selected_paths)

        frames = []
        errors = []

        for result in results:
            if result['status'] == 'ok':
                frames.append({
                    'ad_id': ad_id,
                    'type': 'image',
                    'source': 'video_frame',
                    'base64': result['base64'],
                    'media_type': 'image/jpeg',
                    'filename': result['metadata']['filename'],
                    'size_kb': result['metadata'].get('optimized_size', 0) / 1024,
                    'detail': self.detail_level
                })

                self.stats['total_processed'] += 1
                self.stats['total_size_original'] += result['metadata'].get(
                    'original_size', 0)
                self.stats['total_size_optimized'] += result['metadata'].get(
                    'optimized_size', 0)
            else:
                errors.append({
                    'file': result['file_path'],
                    'error': result['error']
                })
                self.stats['total_errors'] += 1

        return {
            'ad_id': ad_id,
            'frames': frames,
            'count': len(frames),
            'errors': errors
        }

    async def process_multiple_ads(
        self,
        ads_data: List[Dict],
        show_progress: bool = True
    ) -> Dict:
        """
        Procesa múltiples anuncios con imágenes y frames

        Args:
            ads_data: Lista de {
                'ad_id': str,
                'image_paths': [Path, ...],
                'frame_paths': [Path, ...]
            }
            show_progress: Mostrar barra de progreso

        Returns:
            {
                'media_by_ad': {ad_id: {'images': [...], 'frames': [...]}},
                'stats': {...}
            }
        """
        media_by_ad = {}
        tasks = []

        # Crear tareas para imágenes y frames
        for ad_data in ads_data:
            ad_id = ad_data['ad_id']

            if ad_data.get('image_paths'):
                tasks.append(('images', ad_id, self.process_ad_images(
                    ad_id,
                    ad_data['image_paths'],
                    ad_data.get('max_images', 5)
                )))

            if ad_data.get('frame_paths'):
                tasks.append(('frames', ad_id, self.process_ad_frames(
                    ad_id,
                    ad_data['frame_paths'],
                    ad_data.get('max_frames', 10)
                )))

        # Procesar con barra de progreso
        if show_progress:
            results = []
            for task_type, ad_id, coro in async_tqdm(
                tasks,
                desc="Procesando multimedia"
            ):
                result = await coro
                results.append((task_type, ad_id, result))
        else:
            coros = [coro for _, _, coro in tasks]
            task_results = await asyncio.gather(*coros)
            results = [
                (tasks[i][0], tasks[i][1], task_results[i])
                for i in range(len(tasks))
            ]

        # Organizar resultados por anuncio
        for task_type, ad_id, result in results:
            if ad_id not in media_by_ad:
                media_by_ad[ad_id] = {
                    'images': [],
                    'frames': [],
                    'errors': []
                }

            if task_type == 'images':
                media_by_ad[ad_id]['images'] = result['images']
            else:
                media_by_ad[ad_id]['frames'] = result['frames']

            if result.get('errors'):
                media_by_ad[ad_id]['errors'].extend(result['errors'])

        return {
            'media_by_ad': media_by_ad,
            'stats': self.stats
        }

    async def prepare_images_from_urls(
        self,
        urls: List[str],
        desc: str = "Procesando imágenes"
    ) -> List[Dict]:
        """
        Descarga URLs, optimiza y codifica en base64

        Args:
            urls: Lista de URLs de imágenes
            desc: Descripción para barra de progreso

        Returns:
            Lista de resultados {'success': bool, 'base64': str, ...}
        """
        results = []

        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                task = self._download_and_encode(session, url)
                tasks.append(task)

            # Procesar con barra de progreso
            for coro in async_tqdm.as_completed(
                tasks,
                total=len(tasks),
                desc=desc
            ):
                result = await coro
                results.append(result)

        return results

    async def _download_and_encode(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Dict:
        """Descarga URL y codifica"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                image_bytes = await response.read()

            # Optimizar y codificar
            base64_str, metadata = await asyncio.to_thread(
                self.optimizer.optimize_and_encode,
                image_bytes
            )

            return {
                'success': True,
                'base64': base64_str,
                'media_type': 'image/jpeg',
                'size_kb': metadata['optimized_size'] / 1024,
                'url': url
            }

        except Exception as e:
            logger.error(f"Error procesando {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }

    async def prepare_frames_from_directory(
        self,
        frames_dir: Path,
        desc: str = "Procesando frames"
    ) -> List[Dict]:
        """
        Codifica todos los frames de un directorio

        Args:
            frames_dir: Directorio con frames guardados
            desc: Descripción para progreso

        Returns:
            Lista de resultados {'success': bool, 'base64': str, ...}
        """
        # Buscar archivos de imagen
        image_extensions = ('.jpg', '.jpeg', '.png')
        frame_files = [
            f for f in frames_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        if not frame_files:
            logger.warning(f"No se encontraron frames en {frames_dir}")
            return []

        logger.info(f"Procesando {len(frame_files)} frames de {frames_dir}")

        # Procesar en lote
        results_raw = await self.encoder.encode_batch(frame_files)

        # Convertir al formato esperado
        results = []
        for raw in results_raw:
            if raw['status'] == 'ok':
                results.append({
                    'success': True,
                    'base64': raw['base64'],
                    'media_type': 'image/jpeg',
                    'size_kb': raw['metadata']['optimized_size'] / 1024,
                    'path': raw['file_path']
                })
            else:
                results.append({
                    'success': False,
                    'error': raw['error'],
                    'path': raw['file_path']
                })

        return results

    def get_stats_summary(self) -> Dict:
        """Obtiene resumen de estadísticas"""
        compression_ratio = (
            self.stats['total_size_original'] /
            self.stats['total_size_optimized']
            if self.stats['total_size_optimized'] > 0
            else 1
        )

        return {
            **self.stats,
            'compression_ratio': compression_ratio,
            'success_rate': (
                (self.stats['total_processed'] /
                 (self.stats['total_processed'] + self.stats['total_errors']))
                if (self.stats['total_processed'] + self.stats['total_errors']) > 0
                else 0
            )
        }
