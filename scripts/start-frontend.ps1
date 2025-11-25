# Script PowerShell para iniciar solo el servidor Frontend
# Uso: .\scripts\start-frontend.ps1

Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 79) -ForegroundColor Green
Write-Host "🌐 FRONTEND SERVER - Analizador de Anuncios" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 79) -ForegroundColor Green
Write-Host ""

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

Write-Host "🔌 Iniciando servidor Frontend en puerto 3001..." -ForegroundColor Yellow
Write-Host "🌐 URL: http://localhost:3001/" -ForegroundColor Green
Write-Host ""

python frontend_server.py




