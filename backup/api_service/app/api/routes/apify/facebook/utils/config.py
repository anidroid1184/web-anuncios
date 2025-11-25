"""
Configuration and utility functions for Facebook routes
"""
import os
from pathlib import Path
from typing import Optional

# Ruta al root del repo (para resolver rutas relativas desde api_service)
repo_root = Path(__file__).resolve().parents[7]
# Ruta al api_service (carpeta donde se ejecuta la app)
api_root = Path(__file__).resolve().parents[6]


def get_facebook_saved_base() -> Path:
    """Resuelve la carpeta base donde están los datasets guardados de Facebook.
    NUEVA UBICACIÓN: storage/facebook/
    """
    candidates = [
        # Ubicación en app/processors (donde está actualmente)
        api_root / 'app' / 'processors' / 'datasets' / 'saved_datasets' / 'facebook',
        # Nueva estructura: storage/facebook
        api_root / 'storage' / 'facebook',
        # Compatibilidad con estructura antigua
        api_root / 'datasets' / 'datasets' / 'saved_datasets' / 'facebook',
        api_root / 'datasets' / 'saved_datasets' / 'facebook',
        repo_root / 'api_service' / 'app' / 'processors' /
        'datasets' / 'saved_datasets' / 'facebook',
        repo_root / 'api_service' / 'storage' / 'facebook',
        repo_root / 'api_service' / 'datasets' /
        'datasets' / 'saved_datasets' / 'facebook',
        repo_root / 'api_service' / 'datasets' / 'saved_datasets' / 'facebook',
    ]
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    return candidates[0]


# GCS service (Google Cloud Storage) - Singleton
gcs_service = None
_gcs_initialized = False


def get_gcs_service():
    """Get or initialize GCS service singleton"""
    global gcs_service, _gcs_initialized

    if _gcs_initialized:
        return gcs_service

    try:
        from app.services.gcs_service import GCSService

        credentials_path = None
        # 1) variables de entorno
        if os.getenv('GOOGLE_CREDENTIALS_PATH'):
            credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
        elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        else:
            # 2) buscar en rutas conocidas
            candidates = [
                api_root / 'credentials' / 'credentials.json',
                repo_root / 'shared' / 'credentials' / 'credentials.json',
            ]
            for c in candidates:
                try:
                    if c and c.exists():
                        credentials_path = str(c)
                        break
                except Exception:
                    continue

        if credentials_path:
            gcs_service = GCSService(
                credentials_path=credentials_path,
                bucket_name=os.getenv('GOOGLE_BUCKET_NAME', 'proveedor-1')
            )
            print(
                f"✅ GCS service initialized with bucket: {os.getenv('GOOGLE_BUCKET_NAME', 'proveedor-1')}")
        else:
            print("⚠️  GCS credentials not found, service disabled")

    except Exception as e:
        print(f"⚠️  GCS service initialization failed: {e}")

    _gcs_initialized = True
    return gcs_service


# Initialize on module import
gcs_service = get_gcs_service()
