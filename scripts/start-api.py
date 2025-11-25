"""
Script para iniciar solo el servidor API.

Uso:
    python scripts/start-api.py
"""
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Importar y ejecutar el servidor API
if __name__ == "__main__":
    import os
    import sys
    
    # Cambiar al directorio api_service para que los imports funcionen
    api_service_dir = root_dir / "api_service"
    os.chdir(api_service_dir)
    
    # Agregar api_service al path para imports
    sys.path.insert(0, str(api_service_dir))
    
    import uvicorn
    
    host = os.getenv('API_HOST', '127.0.0.1')
    port = int(os.getenv('PORT') or os.getenv('API_PORT') or 8001)
    debug_env = os.getenv('DEBUG', 'False')
    reload_flag = str(debug_env).lower() in ('1', 'true', 'yes')
    
    print("=" * 80)
    print("📡 API SERVER - Analizador de Anuncios")
    print("=" * 80)
    print(f"🔌 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🔄 Reload: {reload_flag}")
    print(f"🌐 URL: http://localhost:{port}/")
    print(f"📚 Docs: http://localhost:{port}/docs")
    print("=" * 80)
    print("Press CTRL+C to stop the server")
    print("=" * 80)
    
    # Usar string "main:app" para que uvicorn encuentre el módulo
    uvicorn.run("main:app", host=host, port=port, reload=reload_flag)

