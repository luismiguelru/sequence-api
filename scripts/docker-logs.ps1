Param(
  [string]$Service = "api",
  [int]$Lines = 50,
  [switch]$All
)

# Verificar si docker compose está disponible
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker no está instalado o no está en el PATH" -ForegroundColor Red
    exit 1
}

# Verificar si el servicio existe
$services = docker compose ps --services 2>$null
if ($services -and $Service -notin $services) {
    Write-Host "[ERROR] Service '$Service' not found. Available services: $($services -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host "[docker] Tailing logs for: $Service" -ForegroundColor Cyan
if ($All) {
    Write-Host "[docker] Showing all logs (use -Lines to limit)" -ForegroundColor Yellow
    docker compose logs -f $Service
} else {
    Write-Host "[docker] Showing last $Lines lines (use -All for complete logs)" -ForegroundColor Yellow
    docker compose logs -f --tail=$Lines $Service
}

