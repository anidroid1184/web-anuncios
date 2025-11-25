#!/bin/bash
# Script Bash para iniciar solo el servidor API
# Uso: ./scripts/start-api.sh

echo "=========================================="
echo "📡 API SERVER - Analizador de Anuncios"
echo "=========================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR/api_service"

echo "🔌 Iniciando servidor API en puerto 8001..."
echo "📚 Documentación: http://localhost:8001/docs"
echo ""

python main.py




