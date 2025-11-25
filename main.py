"""
Main entry point for the Ads Analyzer application.

This file starts both servers:
- Frontend server on port 3001
- API server on port 8001

Run with: python main.py
"""
import subprocess
import sys
import os
from pathlib import Path
import time

def start_servers():
    """Start both frontend and API servers in separate processes."""
    
    print("=" * 80)
    print("🚀 ANALIZADOR DE ANUNCIOS - Starting Application")
    print("=" * 80)
    
    # Get Python executable from virtual environment
    python_exe = sys.executable
    
    # Paths
    root_dir = Path(__file__).parent
    api_script = root_dir / "api_service" / "main.py"
    frontend_script = root_dir / "frontend_server.py"
    
    # Check if scripts exist
    if not api_script.exists():
        print(f"❌ Error: API script not found at {api_script}")
        return
    
    if not frontend_script.exists():
        print(f"❌ Error: Frontend script not found at {frontend_script}")
        return
    
    print("\n📡 Starting API Server (Port 8001)...")
    print(f"   Command: {python_exe} {api_script}")
    
    # Start API server
    api_process = subprocess.Popen(
        [python_exe, str(api_script)],
        cwd=str(root_dir),
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )
    
    # Wait a bit for API to start
    time.sleep(2)
    
    print("\n🌐 Starting Frontend Server (Port 3001)...")
    print(f"   Command: {python_exe} {frontend_script}")
    
    # Start frontend server
    frontend_process = subprocess.Popen(
        [python_exe, str(frontend_script)],
        cwd=str(root_dir),
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )
    
    print("\n" + "=" * 80)
    print("✅ Both servers started successfully!")
    print("=" * 80)
    print(f"🌐 Frontend: http://localhost:3001")
    print(f"📡 API:      http://localhost:8001")
    print(f"📚 API Docs: http://localhost:8001/docs")
    print("=" * 80)
    print("\n💡 Two console windows have been opened:")
    print("   1. API Server (port 8001)")
    print("   2. Frontend Server (port 3001)")
    print("\n⚠️  To stop the servers, close both console windows or press CTRL+C in each")
    print("=" * 80)
    
    try:
        # Keep this process alive
        print("\n⏳ Main process running... Press CTRL+C to stop all servers\n")
        api_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping servers...")
        api_process.terminate()
        frontend_process.terminate()
        print("👋 Servers stopped")

if __name__ == "__main__":
    start_servers()
