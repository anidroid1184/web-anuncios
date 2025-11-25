"""
Configuración y constantes para el dataset de TikTok
Maneja variables de entorno y rutas del proyecto
"""
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class TikTokDatasetSettings:
    """Configuración centralizada para el manejo de datasets de TikTok"""

    # Credenciales Apify
    apify_token: str = os.getenv("APIFY_TOKEN", "")

    # Directorios base
    root_dir: Path = Path(os.getenv("ROOT_DIR", ".")).resolve()
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))

    # Rutas específicas
    raw_items_path: Path = Path(
        os.getenv(
            "RAW_ITEMS_PATH",
            "data/raw/tiktok_items.json"
        )
    )
    out_dir: Path = Path(
        os.getenv(
            "OUT_DIR",
            "data/dataset_tiktok"
        )
    )

    # Configuración de imágenes
    img_subdir: str = os.getenv("IMG_SUBDIR", "images")

    # Configuración de descarga
    max_workers: int = int(os.getenv("MAX_WORKERS", "16"))
    page_size: int = int(os.getenv("PAGE_SIZE", "1000"))

    # Configuración de requests
    download_timeout: int = int(os.getenv("DOWNLOAD_TIMEOUT", "25"))
    download_retries: int = int(os.getenv("DOWNLOAD_RETRIES", "4"))

    def images_dir(self) -> Path:
        """Retorna el path completo al directorio de imágenes"""
        return self.out_dir / self.img_subdir

    def ensure_directories(self) -> None:
        """Crea los directorios necesarios si no existen"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_items_path.parent.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir().mkdir(parents=True, exist_ok=True)


# Instancia global de configuración
SETTINGS = TikTokDatasetSettings()
