Param(
  [switch]$Rebuild,
  [switch]$Follow
)

Write-Host "[docker] Starting services..." -ForegroundColor Cyan

# Verificar si docker compose está disponible
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker no está instalado o no está en el PATH" -ForegroundColor Red
    exit 1
}

$args = @("up", "-d")
if ($Rebuild) { 
    $args += "--build"
    Write-Host "[docker] Rebuilding images..." -ForegroundColor Yellow
}

docker compose @args

if ($LASTEXITCODE -ne 0) { 
    Write-Host "[ERROR] Failed to start services" -ForegroundColor Red
    exit $LASTEXITCODE 
}

Write-Host "[docker] Services are up!" -ForegroundColor Green
Write-Host "  - API: http://localhost:8000" -ForegroundColor White
Write-Host "  - Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Health: http://localhost:8000/health" -ForegroundColor White

if ($Follow) {
    Write-Host "[docker] Following logs (Ctrl+C to stop)..." -ForegroundColor Cyan
    docker compose logs -f api
}

