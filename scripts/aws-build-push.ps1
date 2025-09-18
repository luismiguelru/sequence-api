Param(
  [string]$AWSRegion = "us-east-1",
  [string]$AWSProfile = "default",
  [string]$RepositoryName = "sequence-api"
)

$ErrorActionPreference = "Stop"

Write-Host "[AWS] Building and pushing Docker image..." -ForegroundColor Cyan

# Verificar AWS CLI
if (-not (Get-Command "aws" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] AWS CLI no está instalado" -ForegroundColor Red
    exit 1
}

# Verificar Docker
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker no está instalado" -ForegroundColor Red
    exit 1
}

# Configurar AWS
$env:AWS_PROFILE = $AWSProfile

# Obtener account ID
$accountId = aws sts get-caller-identity --query Account --output text
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] No se pudo obtener AWS account ID" -ForegroundColor Red
    exit 1
}

$ecrUri = "$accountId.dkr.ecr.$AWSRegion.amazonaws.com/$RepositoryName"

Write-Host "[AWS] ECR URI: $ecrUri" -ForegroundColor Yellow

# Crear ECR repository si no existe
Write-Host "[AWS] Creating ECR repository..." -ForegroundColor Yellow
aws ecr create-repository --repository-name $RepositoryName --region $AWSRegion 2>$null

# Login a ECR
Write-Host "[AWS] Logging in to ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $AWSRegion | docker login --username AWS --password-stdin $ecrUri

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to login to ECR" -ForegroundColor Red
    exit 1
}

# Build de la imagen
Write-Host "[AWS] Building Docker image..." -ForegroundColor Yellow
docker build -f Dockerfile.prod -t $RepositoryName:latest .

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker build failed" -ForegroundColor Red
    exit 1
}

# Tag para ECR
docker tag $RepositoryName:latest $ecrUri:latest

# Push a ECR
Write-Host "[AWS] Pushing image to ECR..." -ForegroundColor Yellow
docker push $ecrUri:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host "[AWS] Image pushed successfully!" -ForegroundColor Green
    Write-Host "  - Image URI: $ecrUri:latest" -ForegroundColor White
    
    # Actualizar terraform.tfvars si existe
    $tfvarsPath = "terraform/terraform.tfvars"
    if (Test-Path $tfvarsPath) {
        $content = Get-Content $tfvarsPath -Raw
        $content = $content -replace 'ecr_repository_url = ".*"', "ecr_repository_url = `"$ecrUri`""
        Set-Content $tfvarsPath $content
        Write-Host "  - Updated terraform.tfvars with ECR URI" -ForegroundColor White
    }
} else {
    Write-Host "[ERROR] Failed to push image to ECR" -ForegroundColor Red
    exit 1
}
