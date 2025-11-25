"""
Utilidades compartidas para los módulos de Facebook
"""

from pathlib import Path
import os

# Rutas base
repo_root = Path(__file__).resolve().parents[7]
api_root = Path(__file__).resolve().parents[6]


def get_facebook_saved_base() -> Path:
    """
    Resuelve la carpeta base donde están los datasets guardados de Facebook.
    NUEVA UBICACIÓN: storage/facebook/
    """
    candidates = [
        # Nueva estructura: storage/facebook
        api_root / 'storage' / 'facebook',
        # Compatibilidad con estructura antigua
        api_root / 'datasets' / 'datasets' / 'saved_datasets' / 'facebook',
        api_root / 'datasets' / 'saved_datasets' / 'facebook',
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
