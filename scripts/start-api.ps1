# Script PowerShell para iniciar solo el servidor API
# Uso: .\scripts\start-api.ps1

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "📡 API SERVER - Analizador de Anuncios" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location "$rootDir\api_service"

Write-Host "🔌 Iniciando servidor API en puerto 8001..." -ForegroundColor Yellow
Write-Host "📚 Documentación: http://localhost:8001/docs" -ForegroundColor Green
Write-Host ""

python main.py




