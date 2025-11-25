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



