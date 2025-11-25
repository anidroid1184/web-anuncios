"""
Script mejorado para iniciar el proyecto de forma más limpia.

Este script inicia ambos servidores (API y Frontend) y muestra su output
de forma organizada en una sola terminal con prefijos [API] y [FRONTEND].

Uso:
    python start.py

Para desarrollo individual:
    python start.py --api-only      # Solo inicia el API
    python start.py --frontend-only # Solo inicia el Frontend
"""
import subprocess
import sys
import os
import threading
import signal
from pathlib import Path
from datetime import datetime

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    # Configurar stdout/stderr para UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass
    # También configurar la variable de entorno para subprocess
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Colores para terminal (ANSI escape codes)
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # API colors
    API_BG = '\033[48;5;18m'  # Azul oscuro
    API_FG = '\033[38;5;117m'  # Azul claro
    API = f'{API_BG}{API_FG}'
    
    # Frontend colors
    FRONTEND_BG = '\033[48;5;22m'  # Verde oscuro
    FRONTEND_FG = '\033[38;5;120m'  # Verde claro
    FRONTEND = f'{FRONTEND_BG}{FRONTEND_FG}'
    
    # Status colors
    SUCCESS = '\033[38;5;46m'  # Verde
    ERROR = '\033[38;5;196m'   # Rojo
    WARNING = '\033[38;5;226m' # Amarillo
    INFO = '\033[38;5;51m'     # Cian

# Variables globales para procesos
api_process = None
frontend_process = None
shutdown_flag = threading.Event()

def print_header():
    """Imprime el encabezado del script."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}🚀 ANALIZADOR DE ANUNCIOS - Iniciando Servidores{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

def print_info():
    """Imprime información de los servidores."""
    print(f"{Colors.INFO}📍 URLs disponibles:{Colors.RESET}")
    print(f"   🌐 Frontend: http://localhost:3001/")
    print(f"   📡 API:      http://localhost:8001/")
    print(f"   📚 API Docs: http://localhost:8001/docs")
    print(f"\n{Colors.WARNING}💡 Presiona CTRL+C para detener todos los servidores{Colors.RESET}\n")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

def print_footer():
    """Imprime el pie cuando se detiene."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.INFO}👋 Servidores detenidos{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

def read_output(process, prefix, color):
    """Lee el output de un proceso y lo imprime con prefijo."""
    try:
        # Leer línea por línea
        while True:
            if shutdown_flag.is_set():
                break
            if not process or process.poll() is not None:
                # El proceso terminó
                break
            line = process.stdout.readline()
            if not line:
                # Si no hay línea pero el proceso sigue vivo, esperar un poco
                if process.poll() is None:
                    import time
                    time.sleep(0.1)
                    continue
                break
            if line:
                # Limpiar línea y agregar prefijo con color
                line_clean = line.rstrip()
                if line_clean:  # Solo imprimir líneas no vacías
                    # Intentar usar colores, si falla usar texto plano
                    try:
                        print(f"{color}[{prefix}]{Colors.RESET} {line_clean}")
                    except:
                        print(f"[{prefix}] {line_clean}")
        if process and process.stdout:
            try:
                process.stdout.close()
            except:
                pass
    except Exception as e:
        if not shutdown_flag.is_set():
            try:
                print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Error leyendo output de {prefix}: {e}")
            except:
                print(f"[ERROR] Error leyendo output de {prefix}: {e}")

def check_port(port, name):
    """Verifica si un puerto está disponible."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    
    if result == 0:
        print(f"{Colors.WARNING}⚠️  Advertencia: El puerto {port} ({name}) ya está en uso{Colors.RESET}")
        return False
    return True

def start_api_server():
    """Inicia el servidor API."""
    global api_process
    
    root_dir = Path(__file__).parent
    api_script = root_dir / "api_service" / "main.py"
    python_exe = sys.executable
    
    if not api_script.exists():
        print(f"{Colors.ERROR}❌ Error: No se encontró el script de API en {api_script}{Colors.RESET}")
        return None
    
    # Verificar puerto
    check_port(8001, "API")
    
    print(f"{Colors.API}[API]{Colors.RESET} {Colors.INFO}Iniciando servidor API en puerto 8001...{Colors.RESET}")
    
    # Preparar variables de entorno para subprocess
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        api_process = subprocess.Popen(
            [python_exe, str(api_script)],
            cwd=str(root_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
            encoding='utf-8',
            errors='replace'  # Reemplazar caracteres que no se pueden decodificar
        )
        
        # Thread para leer output
        api_thread = threading.Thread(
            target=read_output,
            args=(api_process, "API", Colors.API),
            daemon=True
        )
        api_thread.start()
        
        return api_process
    except Exception as e:
        print(f"{Colors.ERROR}❌ Error iniciando API: {e}{Colors.RESET}")
        return None

def start_frontend_server():
    """Inicia el servidor Frontend."""
    global frontend_process
    
    root_dir = Path(__file__).parent
    frontend_script = root_dir / "frontend_server.py"
    python_exe = sys.executable
    
    if not frontend_script.exists():
        print(f"{Colors.ERROR}❌ Error: No se encontró el script de Frontend en {frontend_script}{Colors.RESET}")
        return None
    
    # Verificar puerto
    check_port(3001, "Frontend")
    
    print(f"{Colors.FRONTEND}[FRONTEND]{Colors.RESET} {Colors.INFO}Iniciando servidor Frontend en puerto 3001...{Colors.RESET}")
    
    # Preparar variables de entorno para subprocess
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        frontend_process = subprocess.Popen(
            [python_exe, str(frontend_script)],
            cwd=str(root_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
            encoding='utf-8',
            errors='replace'  # Reemplazar caracteres que no se pueden decodificar
        )
        
        # Thread para leer output
        frontend_thread = threading.Thread(
            target=read_output,
            args=(frontend_process, "FRONTEND", Colors.FRONTEND),
            daemon=True
        )
        frontend_thread.start()
        
        return frontend_process
    except Exception as e:
        print(f"{Colors.ERROR}❌ Error iniciando Frontend: {e}{Colors.RESET}")
        return None

def signal_handler(signum, frame):
    """Maneja la señal de interrupción (CTRL+C)."""
    print(f"\n\n{Colors.WARNING}🛑 Deteniendo servidores...{Colors.RESET}")
    shutdown_flag.set()
    stop_servers()
    print_footer()
    sys.exit(0)

def stop_servers():
    """Detiene todos los servidores."""
    global api_process, frontend_process
    
    if api_process:
        try:
            # Intentar terminar de forma suave
            api_process.terminate()
            try:
                api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Si no responde, forzar cierre
                api_process.kill()
                api_process.wait(timeout=2)
        except Exception as e:
            # Si hay error, intentar matar el proceso de todas formas
            try:
                if api_process.poll() is None:
                    api_process.kill()
            except:
                pass
    
    if frontend_process:
        try:
            # Intentar terminar de forma suave
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Si no responde, forzar cierre
                frontend_process.kill()
                frontend_process.wait(timeout=2)
        except Exception as e:
            # Si hay error, intentar matar el proceso de todas formas
            try:
                if frontend_process.poll() is None:
                    frontend_process.kill()
            except:
                pass

def main():
    """Función principal."""
    global api_process, frontend_process
    
    # Registrar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parsear argumentos
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    api_only = '--api-only' in args or '-a' in args
    frontend_only = '--frontend-only' in args or '-f' in args
    
    print_header()
    
    # Iniciar servidores según argumentos
    if api_only:
        api_process = start_api_server()
        if not api_process:
            sys.exit(1)
        print_info()
        print(f"{Colors.SUCCESS}✅ Servidor API iniciado. Presiona CTRL+C para detener.{Colors.RESET}\n")
    elif frontend_only:
        frontend_process = start_frontend_server()
        if not frontend_process:
            sys.exit(1)
        print_info()
        print(f"{Colors.SUCCESS}✅ Servidor Frontend iniciado. Presiona CTRL+C para detener.{Colors.RESET}\n")
    else:
        # Iniciar ambos servidores
        api_process = start_api_server()
        if not api_process:
            sys.exit(1)
        
        # Esperar un poco para que el API se inicie
        import time
        time.sleep(2)
        
        frontend_process = start_frontend_server()
        if not frontend_process:
            stop_servers()
            sys.exit(1)
        
        print_info()
        print(f"{Colors.SUCCESS}✅ Ambos servidores iniciados correctamente{Colors.RESET}\n")
    
    # Esperar a que los procesos terminen o se reciba señal
    # Mantener los procesos vivos y reiniciarlos si fallan
    try:
        if api_only:
            # Mantener el proceso API vivo, reiniciar si falla
            while True:
                if api_process:
                    api_process.wait()
                    if not shutdown_flag.is_set():
                        print(f"{Colors.WARNING}⚠️  El servidor API se detuvo. Reiniciando...{Colors.RESET}")
                        api_process = start_api_server()
                        if not api_process:
                            break
                        import time
                        time.sleep(2)
                else:
                    break
        elif frontend_only:
            # Mantener el proceso Frontend vivo, reiniciar si falla
            while True:
                if frontend_process:
                    frontend_process.wait()
                    if not shutdown_flag.is_set():
                        print(f"{Colors.WARNING}⚠️  El servidor Frontend se detuvo. Reiniciando...{Colors.RESET}")
                        frontend_process = start_frontend_server()
                        if not frontend_process:
                            break
                        import time
                        time.sleep(1)
                else:
                    break
        else:
            # Mantener ambos procesos vivos, reiniciar solo si realmente fallan
            # Nota: Uvicorn con reload puede hacer que parezca que el proceso terminó,
            # pero el reloader principal sigue vivo, así que no reiniciamos en ese caso
            consecutive_api_failures = 0
            consecutive_frontend_failures = 0
            max_consecutive_failures = 3  # Solo reiniciar después de 3 verificaciones consecutivas
            
            while True:
                if shutdown_flag.is_set():
                    break
                
                import time
                time.sleep(3)  # Esperar 3 segundos entre verificaciones
                
                # Verificar API
                api_dead = api_process is None or api_process.poll() is not None
                if api_dead:
                    consecutive_api_failures += 1
                    if consecutive_api_failures >= max_consecutive_failures and not shutdown_flag.is_set():
                        # El proceso realmente terminó (no es solo un reload)
                        exit_code = api_process.returncode if api_process else None
                        print(f"{Colors.WARNING}⚠️  El servidor API se detuvo (exit code: {exit_code}). Reiniciando...{Colors.RESET}")
                        api_process = start_api_server()
                        if api_process:
                            consecutive_api_failures = 0
                            time.sleep(2)
                        else:
                            print(f"{Colors.ERROR}❌ No se pudo reiniciar el servidor API{Colors.RESET}")
                            break
                else:
                    consecutive_api_failures = 0  # Resetear contador si el proceso está vivo
                
                # Verificar Frontend
                frontend_dead = frontend_process is None or frontend_process.poll() is not None
                if frontend_dead:
                    consecutive_frontend_failures += 1
                    if consecutive_frontend_failures >= max_consecutive_failures and not shutdown_flag.is_set():
                        # El proceso realmente terminó
                        exit_code = frontend_process.returncode if frontend_process else None
                        print(f"{Colors.WARNING}⚠️  El servidor Frontend se detuvo (exit code: {exit_code}). Reiniciando...{Colors.RESET}")
                        frontend_process = start_frontend_server()
                        if frontend_process:
                            consecutive_frontend_failures = 0
                            time.sleep(1)
                        else:
                            print(f"{Colors.ERROR}❌ No se pudo reiniciar el servidor Frontend{Colors.RESET}")
                            # Continuar con el API aunque Frontend falle
                else:
                    consecutive_frontend_failures = 0  # Resetear contador si el proceso está vivo
                
                # Si ambos procesos están muertos definitivamente, salir
                if (api_dead and frontend_dead and 
                    consecutive_api_failures >= max_consecutive_failures and 
                    consecutive_frontend_failures >= max_consecutive_failures and
                    not shutdown_flag.is_set()):
                    print(f"{Colors.ERROR}❌ Ambos servidores se detuvieron y no se pudieron reiniciar{Colors.RESET}")
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if not shutdown_flag.is_set():
            shutdown_flag.set()
        stop_servers()

if __name__ == "__main__":
    main()

