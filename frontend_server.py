"""
Simple HTTP server for serving the frontend prototype.

Run this with:
    python frontend_server.py

The frontend will be available at http://localhost:3001
"""
import http.server
import socketserver
import os
import sys
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    # Configurar stdout/stderr para UTF-8
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None
    # También configurar la variable de entorno para Python
    os.environ['PYTHONIOENCODING'] = 'utf-8'

PORT = 3001
DIRECTORY = Path(__file__).parent / "frontend" / "prototype"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def safe_print(text):
    """Imprime texto de forma segura, manejando encoding en Windows."""
    try:
        print(text)
    except (UnicodeEncodeError, UnicodeError):
        # Si falla el encoding, intentar imprimir sin emojis problemáticos
        try:
            # Reemplazar emojis comunes por texto simple
            text_safe = text
            emoji_replacements = {
                '🌐': '[WEB]',
                '📍': '[LOC]',
                '🔌': '[PORT]',
                '📡': '[API]',
                '👋': '[BYE]',
            }
            for emoji, replacement in emoji_replacements.items():
                text_safe = text_safe.replace(emoji, replacement)
            print(text_safe)
        except:
            # Última opción: solo ASCII
            text_ascii = text.encode('ascii', 'ignore').decode('ascii')
            print(text_ascii)

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        safe_print("=" * 80)
        safe_print("🌐 FRONTEND SERVER - Analizador de Anuncios")
        safe_print("=" * 80)
        safe_print(f"📍 Serving from: {DIRECTORY}")
        safe_print(f"🔌 Port: {PORT}")
        safe_print(f"🌐 Frontend: http://localhost:{PORT}/")
        safe_print(f"📡 API Backend: http://localhost:8001/")
        safe_print("=" * 80)
        safe_print("Press CTRL+C to stop the server")
        safe_print("=" * 80)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            safe_print("\n\n👋 Frontend server stopped")
