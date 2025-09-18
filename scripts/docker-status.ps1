Param(
  [switch]$Detailed
)

Write-Host "[docker] Checking service status..." -ForegroundColor Cyan

# Verificar si docker compose está disponible
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker no está instalado o no está en el PATH" -ForegroundColor Red
    exit 1
}

# Mostrar estado de los servicios
Write-Host "`n[docker] Service Status:" -ForegroundColor Yellow
docker compose ps

# Verificar health checks
Write-Host "`n[docker] Health Checks:" -ForegroundColor Yellow
$apiStatus = docker compose ps api --format "table {{.State}}" | Select-Object -Skip 1
if ($apiStatus -eq "running") {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
        if ($response.status -eq "healthy") {
            Write-Host "  ✓ API is healthy" -ForegroundColor Green
        } else {
            Write-Host "  ✗ API is unhealthy: $($response.error)" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ API health check failed: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "  ✗ API is not running" -ForegroundColor Red
}

if ($Detailed) {
    Write-Host "`n[docker] Resource Usage:" -ForegroundColor Yellow
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    
    Write-Host "`n[docker] Volume Usage:" -ForegroundColor Yellow
    docker system df -v
}
