Param(
  [string]$Environment = "production",
  [switch]$Plan,
  [switch]$Apply,
  [switch]$Destroy,
  [string]$AWSProfile = "default"
)

$ErrorActionPreference = "Stop"

Write-Host "[AWS] Starting deployment process..." -ForegroundColor Cyan

# Verificar AWS CLI
if (-not (Get-Command "aws" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] AWS CLI no está instalado" -ForegroundColor Red
    exit 1
}

# Verificar Terraform
if (-not (Get-Command "terraform" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Terraform no está instalado" -ForegroundColor Red
    exit 1
}

# Verificar Docker
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker no está instalado" -ForegroundColor Red
    exit 1
}

# Configurar AWS profile
$env:AWS_PROFILE = $AWSProfile

# Navegar al directorio terraform
Push-Location terraform

try {
    # Inicializar Terraform
    Write-Host "[AWS] Initializing Terraform..." -ForegroundColor Yellow
    terraform init

    if ($LASTEXITCODE -ne 0) {
        throw "Terraform init failed"
    }

    if ($Plan) {
        Write-Host "[AWS] Planning infrastructure changes..." -ForegroundColor Yellow
        terraform plan -var-file="terraform.tfvars"
    }
    elseif ($Apply) {
        Write-Host "[AWS] Applying infrastructure changes..." -ForegroundColor Yellow
        terraform apply -var-file="terraform.tfvars" -auto-approve
        
        if ($LASTEXITCODE -eq 0) {
            $apiUrl = terraform output -raw api_url
            Write-Host "[AWS] Deployment successful!" -ForegroundColor Green
            Write-Host "  - API URL: $apiUrl" -ForegroundColor White
            Write-Host "  - Health Check: $apiUrl/health" -ForegroundColor White
            Write-Host "  - API Docs: $apiUrl/docs" -ForegroundColor White
        }
    }
    elseif ($Destroy) {
        Write-Host "[WARNING] This will destroy all infrastructure!" -ForegroundColor Red
        $confirm = Read-Host "Type 'yes' to confirm"
        if ($confirm -eq "yes") {
            terraform destroy -var-file="terraform.tfvars" -auto-approve
        } else {
            Write-Host "[AWS] Destroy cancelled" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "[AWS] Available options:" -ForegroundColor Cyan
        Write-Host "  -Plan    : Show planned changes" -ForegroundColor White
        Write-Host "  -Apply   : Deploy infrastructure" -ForegroundColor White
        Write-Host "  -Destroy : Destroy infrastructure" -ForegroundColor White
    }
}
finally {
    Pop-Location
}
