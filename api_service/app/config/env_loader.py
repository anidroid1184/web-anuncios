from pathlib import Path
import os
from dotenv import load_dotenv


def load_env(env_path: str | None = None) -> Path:
    """
    Carga el archivo .env para la aplicación.

    - Si `env_path` es None, busca primero en raíz del proyecto, luego en api_service/.env
    - Retorna el Path cargado (útil para registros y debugging).
    """
    if env_path:
        p = Path(env_path)
        if p.exists():
            load_dotenv(dotenv_path=str(p))
            return p

    # Prioridad 1: .env en la raíz del proyecto (parents[3])
    root_env = Path(__file__).resolve().parents[3] / '.env'
    if root_env.exists():
        load_dotenv(dotenv_path=str(root_env))
        return root_env

    # Prioridad 2: .env en api_service (parents[2])
    api_env = Path(__file__).resolve().parents[2] / '.env'
    if api_env.exists():
        load_dotenv(dotenv_path=str(api_env))
        return api_env

    # Fallback: buscar en cwd
    load_dotenv()
    return Path.cwd() / '.env'


def get_env(key: str, default=None):
    return os.getenv(key, default)
