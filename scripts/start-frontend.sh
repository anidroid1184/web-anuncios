#!/bin/bash
# Script Bash para iniciar solo el servidor Frontend
# Uso: ./scripts/start-frontend.sh

echo "=========================================="
echo "🌐 FRONTEND SERVER - Analizador de Anuncios"
echo "=========================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "🔌 Iniciando servidor Frontend en puerto 3001..."
echo "🌐 URL: http://localhost:3001/"
echo ""

python frontend_server.py




