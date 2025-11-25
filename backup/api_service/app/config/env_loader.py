from pathlib import Path
import os
from dotenv import load_dotenv


def load_env(env_path: str | None = None) -> Path:
    """
    Carga el archivo .env para la aplicación.

    - Si `env_path` es None, busca `api_service/.env` relativo a este archivo.
    - Retorna el Path cargado (útil para registros y debugging).
    """
    # `env_loader.py` está en api_service/app/config
    # queremos apuntar a api_service/.env -> parents[2]
    if env_path:
        p = Path(env_path)
    else:
        p = Path(__file__).resolve().parents[2] / '.env'

    if p.exists():
        load_dotenv(dotenv_path=str(p))
    else:
        # intentar cargar sin path (load_dotenv buscará en cwd)
        load_dotenv()

    return p


def get_env(key: str, default=None):
    return os.getenv(key, default)
