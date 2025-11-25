"""
Tests para el endpoint de análisis con Base64
- Test 1: 5 imágenes estáticas
- Test 2: Video con frames extraídos
"""
from fastapi import FastAPI
from app.api.routes.apify.facebook.routes.analysis import router
from fastapi.testclient import TestClient
import pytest
import asyncio
import os
import sys
from pathlib import Path
from PIL import Image
import io

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)


# Crear app de prueba
app = FastAPI()
app.include_router(router)
client = TestClient(app)


def crear_imagen_prueba(width=400, height=300, color=(255, 0, 0)):
    """Crea una imagen de prueba en memoria"""
    img = Image.new('RGB', (width, height), color=color)
    return img


def guardar_imagen_temporal(img, filename):
    """Guarda imagen temporal para simular frames"""
    temp_dir = Path("temp_test_frames")
    temp_dir.mkdir(exist_ok=True)
    filepath = temp_dir / filename
    img.save(filepath, format='JPEG', quality=85)
    return filepath


class TestAnalysisEndpoint:
    """Tests del endpoint analyze-local-only"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Configuración antes de cada test"""
        # Crear directorio temporal para frames
        self.temp_dir = Path("temp_test_frames")
        self.temp_dir.mkdir(exist_ok=True)
        yield
        # Limpiar después del test
        if self.temp_dir.exists():
            for f in self.temp_dir.glob("*"):
                f.unlink()
            self.temp_dir.rmdir()

    def test_analisis_5_imagenes(self, monkeypatch):
        """
        TEST 1: Analizar 5 imágenes estáticas

        Simula un dataset con 1 anuncio que tiene 5 imágenes.
        Verifica que:
        - Se procesen las 5 imágenes
        - Se genere análisis
        - Se devuelvan estadísticas correctas
        """
        # Mock del CSV con snapshot simulado
        import pandas as pd
        import json

        # Crear snapshot con 5 imágenes
        snapshot_data = {
            'images': [
                {'original_image_url': f'https://via.placeholder.com/400/FF0000?text=Img{i}'}
                for i in range(1, 6)
            ],
            'videos': []
        }

        df_mock = pd.DataFrame([{
            'ad_archive_id': 'TEST_IMG_001',
            'snapshot': json.dumps(snapshot_data)
        }])

        # Mock de pandas.read_csv
        def mock_read_csv(path):
            return df_mock

        monkeypatch.setattr(pd, 'read_csv', mock_read_csv)

        # Mock de BatchMediaProcessor para simular descarga exitosa
        from app.processors.media_preparation import BatchMediaProcessor

        original_prepare = BatchMediaProcessor.prepare_images_from_urls

        async def mock_prepare_images(self, urls, desc=None):
            """Simula descarga exitosa de imágenes"""
            results = []
            for idx, url in enumerate(urls):
                # Crear imagen pequeña en base64
                img = crear_imagen_prueba(200, 150, (255, idx*50, 0))
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                import base64
                b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

                results.append({
                    'success': True,
                    'base64': b64,
                    'media_type': 'image/jpeg',
                    'size_kb': len(b64) / 1024
                })
            return results

        monkeypatch.setattr(
            BatchMediaProcessor,
            'prepare_images_from_urls',
            mock_prepare_images
        )

        # Mock de OpenAI
        from openai import AsyncOpenAI

        class MockCompletion:
            class Choice:
                class Message:
                    content = """
                    ANÁLISIS DE ANUNCIOS:
                    
                    AD TEST_IMG_001:
                    - 5 imágenes analizadas
                    - Paleta de colores cálidos (rojo-naranja)
                    - Diseño simple y directo
                    - Recomendación: Mantener consistencia visual
                    """
                choices = [Choice()]

            class Usage:
                total_tokens = 450

            usage = Usage()
            choices = [Choice()]

        async def mock_create(*args, **kwargs):
            # Verificar que se enviaron imágenes
            messages = kwargs.get('messages', [])
            content = messages[0].get('content', [])

            # Contar imágenes en content
            img_count = sum(1 for item in content if item.get(
                'type') == 'image_url')
            assert img_count == 5, f"Se esperaban 5 imágenes, se recibieron {img_count}"

            return MockCompletion()

        monkeypatch.setattr(
            AsyncOpenAI,
            'chat',
            type('obj', (), {'completions': type(
                'obj', (), {'create': mock_create})})()
        )

        # Ejecutar test
        response = client.post(
            '/analyze-local-only',
            json={
                'run_id': 'test_run_images',
                'top_n': 1
            }
        )

        # Verificaciones
        assert response.status_code == 200
        data = response.json()

        assert data['status'] == 'success'
        assert data['analyzed_ads'] == 1
        assert data['media_summary']['static_images'] == 5
        assert data['media_summary']['video_frames'] == 0
        assert data['media_summary']['total'] == 5
        assert data['tokens_used'] == 450
        assert 'análisis' in data['analysis'].lower()

        print("\n✅ TEST 1 PASADO: 5 imágenes procesadas correctamente")

    def test_analisis_video_con_frames(self, monkeypatch):
        """
        TEST 2: Analizar video con extracción de frames

        Simula un dataset con 1 anuncio que tiene 1 video.
        Verifica que:
        - Se extraigan frames del video
        - Se conviertan a Base64
        - Se envíen a OpenAI
        - Se devuelvan estadísticas correctas
        """
        import pandas as pd
        import json

        # Crear snapshot con 1 video
        snapshot_data = {
            'images': [],
            'videos': [
                {'video_hd_url': 'https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4'}
            ]
        }

        df_mock = pd.DataFrame([{
            'ad_archive_id': 'TEST_VIDEO_001',
            'snapshot': json.dumps(snapshot_data)
        }])

        # Mock de pandas.read_csv
        def mock_read_csv(path):
            return df_mock

        monkeypatch.setattr(pd, 'read_csv', mock_read_csv)

        # Mock de VideoFrameExtractor
        from app.processors.video_processor import VideoFrameExtractor

        def mock_process_multiple_videos(self, video_urls, ad_id, save_dir):
            """Simula extracción de 2 frames"""
            frames = []
            for i in range(2):
                # Crear frame de prueba
                img = crear_imagen_prueba(640, 480, (0, 100*i, 255))
                filename = f"{ad_id}_frame_{i}.jpg"
                filepath = guardar_imagen_temporal(img, filename)

                frames.append({
                    'path': str(filepath),
                    'frame_index': i,
                    'timestamp': i * 0.5
                })

            return frames

        monkeypatch.setattr(
            VideoFrameExtractor,
            'process_multiple_videos',
            mock_process_multiple_videos
        )

        # Mock de OpenAI
        from openai import AsyncOpenAI

        class MockCompletion:
            class Choice:
                class Message:
                    content = """
                    ANÁLISIS DE VIDEO:
                    
                    AD TEST_VIDEO_001:
                    - 2 frames analizados
                    - Video con movimiento
                    - Paleta azul dominante
                    - Narrativa visual clara
                    - Recomendación: Frame inicial muy impactante
                    """
                choices = [Choice()]

            class Usage:
                total_tokens = 380

            usage = Usage()
            choices = [Choice()]

        async def mock_create(*args, **kwargs):
            # Verificar que se enviaron frames
            messages = kwargs.get('messages', [])
            content = messages[0].get('content', [])

            # Contar frames en content
            frame_count = sum(
                1 for item in content if item.get('type') == 'image_url')
            assert frame_count == 2, f"Se esperaban 2 frames, se recibieron {frame_count}"

            # Verificar que son Base64
            for item in content:
                if item.get('type') == 'image_url':
                    url = item['image_url']['url']
                    assert url.startswith(
                        'data:image/jpeg;base64,'), "Frame debe ser Base64"

            return MockCompletion()

        monkeypatch.setattr(
            AsyncOpenAI,
            'chat',
            type('obj', (), {'completions': type(
                'obj', (), {'create': mock_create})})()
        )

        # Ejecutar test
        response = client.post(
            '/analyze-local-only',
            json={
                'run_id': 'test_run_video',
                'top_n': 1
            }
        )

        # Verificaciones
        assert response.status_code == 200
        data = response.json()

        assert data['status'] == 'success'
        assert data['analyzed_ads'] == 1
        assert data['media_summary']['static_images'] == 0
        assert data['media_summary']['video_frames'] == 2
        assert data['media_summary']['total'] == 2
        assert data['tokens_used'] == 380
        assert 'video' in data['analysis'].lower()

        print("\n✅ TEST 2 PASADO: Video con frames procesado correctamente")

    def test_analisis_mixto(self, monkeypatch):
        """
        TEST 3 (BONUS): Anuncio con imágenes Y video

        Verifica el procesamiento mixto:
        - 2 imágenes estáticas
        - 1 video con 2 frames
        - Total: 4 elementos multimedia
        """
        import pandas as pd
        import json

        # Snapshot con imágenes y video
        snapshot_data = {
            'images': [
                {'original_image_url': 'https://via.placeholder.com/400/00FF00?text=Img1'},
                {'original_image_url': 'https://via.placeholder.com/400/00FF00?text=Img2'}
            ],
            'videos': [
                {'video_hd_url': 'https://sample-videos.com/video.mp4'}
            ]
        }

        df_mock = pd.DataFrame([{
            'ad_archive_id': 'TEST_MIXED_001',
            'snapshot': json.dumps(snapshot_data)
        }])

        monkeypatch.setattr(pd, 'read_csv', lambda path: df_mock)

        # Mock BatchMediaProcessor
        from app.processors.media_preparation import BatchMediaProcessor

        async def mock_prepare_images(self, urls, desc=None):
            results = []
            for url in urls:
                img = crear_imagen_prueba(200, 150, (0, 255, 0))
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                import base64
                b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

                results.append({
                    'success': True,
                    'base64': b64,
                    'media_type': 'image/jpeg',
                    'size_kb': len(b64) / 1024
                })
            return results

        monkeypatch.setattr(
            BatchMediaProcessor,
            'prepare_images_from_urls',
            mock_prepare_images
        )

        # Mock VideoFrameExtractor
        from app.processors.video_processor import VideoFrameExtractor

        def mock_process_multiple_videos(self, video_urls, ad_id, save_dir):
            frames = []
            for i in range(2):
                img = crear_imagen_prueba(640, 480, (255, 255, 0))
                filename = f"{ad_id}_frame_{i}.jpg"
                filepath = guardar_imagen_temporal(img, filename)
                frames.append({
                    'path': str(filepath),
                    'frame_index': i,
                    'timestamp': i * 0.5
                })
            return frames

        monkeypatch.setattr(
            VideoFrameExtractor,
            'process_multiple_videos',
            mock_process_multiple_videos
        )

        # Mock OpenAI
        from openai import AsyncOpenAI

        class MockCompletion:
            class Choice:
                class Message:
                    content = "Análisis mixto: 2 imágenes + 2 frames de video"
                choices = [Choice()]

            class Usage:
                total_tokens = 520

            usage = Usage()
            choices = [Choice()]

        async def mock_create(*args, **kwargs):
            messages = kwargs.get('messages', [])
            content = messages[0].get('content', [])
            media_count = sum(
                1 for item in content if item.get('type') == 'image_url')
            assert media_count == 4, f"Se esperaban 4 elementos, se recibieron {media_count}"
            return MockCompletion()

        monkeypatch.setattr(
            AsyncOpenAI,
            'chat',
            type('obj', (), {'completions': type(
                'obj', (), {'create': mock_create})})()
        )

        # Ejecutar test
        response = client.post(
            '/analyze-local-only',
            json={
                'run_id': 'test_run_mixed',
                'top_n': 1
            }
        )

        # Verificaciones
        assert response.status_code == 200
        data = response.json()

        assert data['status'] == 'success'
        assert data['media_summary']['static_images'] == 2
        assert data['media_summary']['video_frames'] == 2
        assert data['media_summary']['total'] == 4

        print("\n✅ TEST 3 PASADO: Procesamiento mixto (imágenes + video)")


if __name__ == "__main__":
    """Ejecutar tests directamente"""
    print("="*80)
    print("🧪 EJECUTANDO TESTS DE ANÁLISIS CON BASE64")
    print("="*80)

    # Configurar pytest para ejecutar
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"  # Mostrar prints
    ])
