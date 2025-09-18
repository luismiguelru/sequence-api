Param(
  [switch]$PruneVolumes,
  [switch]$Follow
)

Write-Host "[docker] Stopping services..." -ForegroundColor Yellow

# Verificar si docker compose está disponible
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker no está instalado o no está en el PATH" -ForegroundColor Red
    exit 1
}

if ($PruneVolumes) {
    Write-Host "[docker] Removing volumes (data will be lost)..." -ForegroundColor Red
    docker compose down -v
} else {
    docker compose down
}

if ($LASTEXITCODE -ne 0) { 
    Write-Host "[ERROR] Failed to stop services" -ForegroundColor Red
    exit $LASTEXITCODE 
}

Write-Host "[docker] Starting services (rebuild)..." -ForegroundColor Cyan
docker compose up -d --build

if ($LASTEXITCODE -ne 0) { 
    Write-Host "[ERROR] Failed to start services" -ForegroundColor Red
    exit $LASTEXITCODE 
}

Write-Host "[docker] Restart complete!" -ForegroundColor Green
Write-Host "  - API: http://localhost:8000" -ForegroundColor White
Write-Host "  - Docs: http://localhost:8000/docs" -ForegroundColor White

if ($Follow) {
    Write-Host "[docker] Following logs (Ctrl+C to stop)..." -ForegroundColor Cyan
    docker compose logs -f api
}

