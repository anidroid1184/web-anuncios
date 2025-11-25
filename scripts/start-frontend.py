"""
Script para iniciar solo el servidor Frontend.

Uso:
    python scripts/start-frontend.py
"""
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Importar y ejecutar el servidor Frontend
if __name__ == "__main__":
    from frontend_server import *
    import socketserver
    
    print("=" * 80)
    print("🌐 FRONTEND SERVER - Analizador de Anuncios")
    print("=" * 80)
    print(f"📍 Serving from: {DIRECTORY}")
    print(f"🔌 Port: {PORT}")
    print(f"🌐 Frontend: http://localhost:{PORT}/")
    print(f"📡 API Backend: http://localhost:8001/")
    print("=" * 80)
    print("Press CTRL+C to stop the server")
    print("=" * 80)
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Frontend server stopped")




