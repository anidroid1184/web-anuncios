"""
Facebook Routes - Configuración y Utilidades
PathResolver, gestión de credenciales, rutas de datasets
"""

import os
from pathlib import Path
from typing import Optional


class PathResolver:
    """
    Resuelve rutas de proyecto aplicando principio de Single Responsibility.
    Gestiona ubicaciones de datasets, credenciales y archivos del proyecto.
    """

    def __init__(self):
        """Inicializa las rutas base del proyecto"""
        current_file = Path(__file__).resolve()
        self.repo_root = current_file.parents[7]  # Root del repositorio
        self.api_root = current_file.parents[6]   # Carpeta api_service

    def get_facebook_saved_base(self) -> Path:
        """
        Resuelve la carpeta base para datasets guardados de Facebook.
        Prioriza nueva estructura (storage/facebook), 
        con fallback a estructura antigua.

        Returns:
            Path: Ruta base para datasets de Facebook
        """
        candidates = [
            # Nueva estructura: storage/facebook
            self.api_root / 'storage' / 'facebook',
            # Compatibilidad con estructura antigua
            self.api_root / 'datasets' / 'datasets' /
            'saved_datasets' / 'facebook',
            self.api_root / 'datasets' / 'saved_datasets' / 'facebook',
            self.repo_root / 'api_service' / 'storage' / 'facebook',
            self.repo_root / 'api_service' / 'datasets' /
            'datasets' / 'saved_datasets' / 'facebook',
            self.repo_root / 'api_service' / 'datasets' /
            'saved_datasets' / 'facebook',
        ]

        for candidate in candidates:
            try:
                if candidate.exists():
                    return candidate
            except Exception:
                continue

        # Retorna primera opción si ninguna existe (se creará si es necesario)
        return candidates[0]

    def get_credentials_path(self, service: str = 'drive') -> Optional[str]:
        """
        Resuelve la ruta de credenciales para un servicio específico.
        Prioriza variables de entorno sobre archivos locales.

        Args:
            service: Tipo de servicio ('drive', 'gcs', 'google')

        Returns:
            Optional[str]: Ruta absoluta a las credenciales o None
        """
        candidates = []

        # 1) Prioridad: Variables de entorno
        env_vars = [
            'GOOGLE_CREDENTIALS_PATH',
            'GOOGLE_DRIVE_CREDENTIALS_PATH',
            'GOOGLE_APPLICATION_CREDENTIALS'
        ]
        for env_var in env_vars:
            value = os.getenv(env_var)
            if value:
                candidates.append(Path(value))

        # 2) Ruta dentro de api_service/credentials
        if service == 'drive':
            candidates.append(
                self.api_root / 'credentials' / 'credsDrive.json'
            )
        candidates.append(
            self.api_root / 'credentials' / 'credentials.json'
        )

        # 3) Ruta compartida en repo root
        candidates.append(
            self.repo_root / 'shared' / 'credentials' / 'credsDrive.json'
        )
        candidates.append(
            self.repo_root / 'shared' / 'credentials' / 'credentials.json'
        )

        # Elegir el primer candidato existente
        for candidate in candidates:
            try:
                if candidate and candidate.exists():
                    return str(candidate)
            except Exception:
                continue

        # Fallback: retornar valor de ENV aunque no exista en disco
        return os.getenv('GOOGLE_CREDENTIALS_PATH') or \
            os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH')


# Singleton global para uso en toda la aplicación
path_resolver = PathResolver()


def get_facebook_saved_base() -> Path:
    """
    Helper function para compatibilidad con código existente.
    Usa el singleton global PathResolver.

    Returns:
        Path: Ruta base para datasets de Facebook
    """
    return path_resolver.get_facebook_saved_base()
