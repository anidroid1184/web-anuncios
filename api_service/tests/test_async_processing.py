"""
Test script para verificar la integración del procesamiento asíncrono
"""
import logging
import asyncio
import sys
import os
from pathlib import Path

# Agregar directorio raíz al PYTHONPATH
api_service_dir = Path(__file__).resolve().parent.parent
if str(api_service_dir) not in sys.path:
    sys.path.insert(0, str(api_service_dir))

# Cambiar al directorio api_service para imports relativos
os.chdir(str(api_service_dir))


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_batch_processor():
    """Prueba el BatchMediaProcessor con imágenes locales"""
    from app.processors.media_preparation import BatchMediaProcessor
    from PIL import Image
    import tempfile

    logger.info("="*60)
    logger.info("TEST: BatchMediaProcessor")
    logger.info("="*60)

    # Crear procesador
    processor = BatchMediaProcessor(max_image_size=1024, max_concurrent=5)

    # Crear imágenes de prueba temporales
    temp_dir = Path(tempfile.mkdtemp())
    test_files = []

    colors = [
        ('red', (255, 0, 0)),
        ('green', (0, 255, 0)),
        ('blue', (0, 0, 255))
    ]

    for name, rgb in colors:
        img = Image.new('RGB', (800, 600), color=rgb)
        file_path = temp_dir / f"test_{name}.jpg"
        img.save(file_path, 'JPEG', quality=95)
        test_files.append(file_path)

    logger.info(f"\n📥 Procesando {len(test_files)} imágenes locales...")

    try:
        # Procesar desde directorio
        results = await processor.prepare_frames_from_directory(
            temp_dir,
            desc="Test images"
        )

        # Verificar resultados
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]

        logger.info(f"\n✅ Resultados:")
        logger.info(f"   Exitosos: {len(successful)}/{len(results)}")
        logger.info(f"   Fallidos: {len(failed)}/{len(results)}")

        # Mostrar detalles de exitosos
        if successful:
            logger.info(f"\n📊 Imágenes procesadas exitosamente:")
            for idx, result in enumerate(successful, 1):
                size_kb = result['size_kb']
                logger.info(
                    f"   [{idx}] {result['media_type']}, "
                    f"{size_kb:.1f} KB, "
                    f"base64: {len(result['base64'])} chars"
                )

        # Mostrar detalles de fallos
        if failed:
            logger.error(f"\n❌ Errores encontrados:")
            for idx, result in enumerate(failed, 1):
                error_msg = result.get('error', 'Unknown error')
                path = result.get('path', 'Unknown path')
                logger.error(f"   [{idx}] {path}")
                logger.error(f"       Error: {error_msg}")

        # Limpiar archivos temporales
        for f in test_files:
            if f.exists():
                f.unlink()
        temp_dir.rmdir()

        return len(successful) > 0

    except Exception as e:
        logger.error(f"❌ Error en prueba: {e}", exc_info=True)
        return False


async def test_image_optimizer():
    """Prueba el ImageOptimizer"""
    from app.processors.media_preparation.image_optimizer import (
        ImageOptimizer
    )
    import io
    from PIL import Image

    logger.info("="*60)
    logger.info("TEST: ImageOptimizer")
    logger.info("="*60)

    try:
        optimizer = ImageOptimizer(max_width=512, max_height=512)

        # Crear imagen de prueba grande
        test_img = Image.new('RGB', (2000, 1500), color=(255, 0, 0))

        # Guardar en memoria
        buffer = io.BytesIO()
        test_img.save(buffer, format='JPEG')
        buffer.seek(0)

        original_size = len(buffer.getvalue())
        logger.info(
            f"\n📸 Imagen original: 2000x1500, {original_size/1024:.1f} KB")

        # Optimizar
        optimized_bytes, metadata = optimizer.optimize_image_bytes(
            buffer.getvalue()
        )

        # Verificar resultado
        opt_size = metadata['optimized_size']
        final_dims = metadata['final_dimensions']

        logger.info(
            f"✅ Imagen optimizada: {final_dims[0]}x{final_dims[1]}, "
            f"{opt_size/1024:.1f} KB"
        )
        logger.info(f"   Reducción: {(1 - opt_size/original_size)*100:.1f}%")

        return final_dims[0] <= 512 or final_dims[1] <= 512

    except Exception as e:
        logger.error(f"❌ Error en prueba: {e}", exc_info=True)
        return False


async def test_async_encoder():
    """Prueba el AsyncMediaEncoder"""
    from app.processors.media_preparation.async_encoder import (
        AsyncMediaEncoder
    )
    import tempfile
    from PIL import Image

    logger.info("="*60)
    logger.info("TEST: AsyncMediaEncoder")
    logger.info("="*60)

    try:
        encoder = AsyncMediaEncoder(max_concurrent=3)

        # Crear imágenes de prueba temporales
        test_files = []
        temp_dir = Path(tempfile.mkdtemp())

        colors = {
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255)
        }

        for name, rgb in colors.items():
            img = Image.new('RGB', (400, 300), color=rgb)
            file_path = temp_dir / f"test_{name}.jpg"
            img.save(file_path)
            test_files.append(file_path)

        logger.info(f"\n📦 Codificando {len(test_files)} imágenes...")

        results = await encoder.encode_batch(test_files)

        successful = [r for r in results if r['status'] == 'ok']

        logger.info(f"\n✅ Codificadas: {len(successful)}/{len(results)}")

        for idx, result in enumerate(successful):
            logger.info(
                f"   [{idx+1}] Base64 length: {len(result['base64'])}"
            )

        # Limpiar archivos temporales
        for f in test_files:
            f.unlink()
        temp_dir.rmdir()

        return len(successful) > 0

    except Exception as e:
        logger.error(f"❌ Error en prueba: {e}", exc_info=True)
        return False


async def main():
    """Ejecuta todas las pruebas"""
    logger.info("\n" + "="*60)
    logger.info("🧪 INICIANDO PRUEBAS DE PROCESAMIENTO ASÍNCRONO")
    logger.info("="*60 + "\n")

    results = {}

    # Test 1: ImageOptimizer
    logger.info("\n[TEST 1/3] ImageOptimizer")
    results['optimizer'] = await test_image_optimizer()

    # Test 2: AsyncMediaEncoder
    logger.info("\n[TEST 2/3] AsyncMediaEncoder")
    results['encoder'] = await test_async_encoder()

    # Test 3: BatchMediaProcessor (integración completa)
    logger.info("\n[TEST 3/3] BatchMediaProcessor (Integración)")
    results['batch_processor'] = await test_batch_processor()

    # Resumen
    logger.info("\n" + "="*60)
    logger.info("📊 RESUMEN DE PRUEBAS")
    logger.info("="*60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    logger.info("="*60)
    if all_passed:
        logger.info("✅ TODAS LAS PRUEBAS PASARON")
    else:
        logger.info("❌ ALGUNAS PRUEBAS FALLARON")
    logger.info("="*60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
