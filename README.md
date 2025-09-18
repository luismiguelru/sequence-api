# Sequence API - Subsecuencia Generator Service

API REST para generar y gestionar subsecuencias de productos para sistemas de recomendación en e-commerce.

## 📋 Descripción

Este servicio procesa secuencias de IDs de productos (historial de compras) y genera todas las subsecuencias posibles para alimentar algoritmos de recomendación. Implementa autenticación JWT y almacenamiento persistente en MongoDB.

## 🚀 Quick Start

### Requisitos previos
- Docker y Docker Compose
- Python 3.11+ (para desarrollo local)

### Instalación y ejecución

1. **Clonar el repositorio**
```bash
git clone https://github.com/luismiguelru/sequence-api.git
cd sequence-api
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

3. **Ejecutar con Docker Compose**
```bash
docker-compose up -d
```

La API estará disponible en `http://localhost:8000`

### Verificar que está funcionando
```bash
curl http://localhost:8000/docs
```

## 🔧 Configuración

### Variables de entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# JWT Configuration
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MIN=10

# MongoDB Configuration
MONGODB_URI=mongodb://mongo:27017
MONGODB_DB=seqdb
MONGODB_SEQ_COL=sequences
MONGODB_SUBSEQ_COL=subsequences
```

## 📚 API Documentation

### Health Check

#### Verificar Estado del Servicio
```bash
GET /health
```

**Response (Healthy):**
```json
{
  "status": "healthy",
  "database": "connected",
  "service": "sequence-api"
}
```

**Response (Unhealthy):**
```json
{
  "status": "unhealthy",
  "database": "disconnected",
  "service": "sequence-api",
  "error": "Connection error details"
}
```

**Nota:** Este endpoint no requiere autenticación y es usado por Docker para health checks.

### Autenticación

#### Obtener Token
```bash
POST /auth/token
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Nota:** El token expira en 10 minutos.

### Endpoints Protegidos

Todos los siguientes endpoints requieren el header:
```
Authorization: Bearer <token>
```

#### Crear Subsecuencias
```bash
POST /sequences
Content-Type: application/json

{
  "items": [1, 2, 3]
}
```

**Response:**
```json
{
  "id": "6745a1b2c3d4e5f6g7h8i9j0",
  "items": [1, 2, 3],
  "total_subsequences": 7
}
```

**Validaciones:**
- IDs deben ser enteros positivos (>0)
- Máximo 18 elementos únicos
- No puede estar vacío

#### Listar Subsecuencias
```bash
GET /subsequences?limit=10
```

**Response:**
```json
[
  {
    "sequence": [1, 2, 3],
    "subSequences": [
      [1], [2], [3],
      [1, 2], [1, 3], [2, 3],
      [1, 2, 3]
    ]
  }
]
```

**Parámetros:**
- `limit`: Número de secuencias a retornar (1-50, default: 10)

## 🧪 Testing

### Ejecutar tests
```bash
# Instalar dependencias de desarrollo
pip install -r requirements.txt

# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov=app --cov-report=term-missing

# Tests específicos
pytest tests/test_auth.py -v
pytest tests/test_endpoints.py -v
```

### Coverage objetivo
- Overall: >80%
- Endpoints críticos: >90%

## 🏗️ Arquitectura

### Estructura del proyecto
```
sequence-api/
├── app/
│   ├── api/
│   │   └── routes.py         # Endpoints FastAPI
│   ├── core/
│   │   └── security.py       # JWT y autenticación
│   ├── db/
│   │   └── mongo.py          # Conexión MongoDB
│   ├── models/
│   │   └── schemas.py        # Modelos Pydantic
│   ├── repositories/
│   │   └── subsequence_repo.py  # Capa de datos
│   ├── services/
│   │   └── subsequence_service.py  # Lógica de negocio
│   └── main.py               # Aplicación FastAPI
├── tests/
│   ├── conftest.py           # Configuración pytest y fixtures
│   ├── test_auth.py          # Tests de autenticación
│   ├── test_bulk_write.py    # Tests de escritura masiva
│   ├── test_deduplication.py # Tests de deduplicación
│   ├── test_endpoints.py     # Tests de endpoints
│   ├── test_services.py      # Tests de servicios
│   └── test_subsequences.py  # Tests de subsecuencias
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                # Continuous Integration
│   │   ├── cd.yml                # Continuous Deployment
│   │   ├── codeql.yml            # Análisis de seguridad
│   │   └── dependency-review.yml # Revisión de dependencias
│   └── dependabot.yml            # Actualizaciones automáticas
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml            # Configuración Black/Ruff
└── .pre-commit-config.yaml   # Hooks pre-commit
```

### Decisiones de diseño

#### 1. **Deduplicación de productos**
Las secuencias se normalizan eliminando duplicados y ordenando. Razones:
- Evita explosión combinatoria (2^n subsecuencias)
- Para recomendaciones importa QUÉ productos compró, no CUÁNTAS veces
- Simplifica el índice único en MongoDB

**Nota:** En producción, mantendríamos las frecuencias para análisis RFM (Recency, Frequency, Monetary).

#### 2. **Límite de 18 elementos**
Con n elementos se generan 2^n - 1 subsecuencias:
- n=18 → 262,143 subsecuencias
- n=20 → 1,048,575 subsecuencias

El límite previene problemas de memoria y performance.

#### 3. **Índice único por hash**
Cada subsecuencia tiene un hash único basado en sus elementos ordenados, evitando duplicados en la base de datos.

## 🚢 Deployment

### Desarrollo local
```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# MongoDB local
docker run -d -p 27017:27017 mongo:7
```

### AWS Production

#### Prerrequisitos
- AWS CLI configurado
- Terraform instalado
- Docker instalado
- Cuenta AWS con permisos para ECS, VPC, DocumentDB, ALB

#### Despliegue paso a paso

1. **Configurar variables de entorno:**
```bash
# Copiar archivo de ejemplo
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# Editar con tus valores
# - docdb_password: contraseña segura para DocumentDB
# - jwt_secret: clave secreta para JWT
# - ecr_repository_url: se actualiza automáticamente
```

2. **Construir y subir imagen Docker:**
```powershell
.\scripts\aws-build-push.ps1 -AWSRegion us-east-1
```

3. **Desplegar infraestructura:**
```powershell
# Ver plan de cambios
.\scripts\aws-deploy.ps1 -Plan

# Aplicar cambios
.\scripts\aws-deploy.ps1 -Apply
```

4. **Verificar despliegue:**
```powershell
# Obtener URL de la API
terraform -chdir=terraform output api_url

# Verificar health check
curl http://[API_URL]/health
```

#### Arquitectura AWS

- **ECS Fargate**: Contenedores sin servidor
- **DocumentDB**: MongoDB compatible (reemplaza MongoDB local)
- **ALB**: Load balancer con health checks
- **VPC**: Red privada con subnets públicas y privadas
- **CloudWatch**: Logs y monitoreo
- **IAM**: Roles y permisos seguros


#### Limpieza
```powershell
# Destruir toda la infraestructura
.\scripts\aws-deploy.ps1 -Destroy
```

### Producción con Docker

#### Scripts de PowerShell
```powershell
# Iniciar servicios
.\scripts\docker-up.ps1

# Iniciar con rebuild
.\scripts\docker-up.ps1 -Rebuild

# Iniciar y seguir logs
.\scripts\docker-up.ps1 -Follow

# Reiniciar servicios
.\scripts\docker-restart.ps1

# Reiniciar y limpiar datos
.\scripts\docker-restart.ps1 -PruneVolumes

# Ver logs
.\scripts\docker-logs.ps1

# Ver logs de MongoDB
.\scripts\docker-logs.ps1 -Service mongo

# Ver estado de servicios
.\scripts\docker-status.ps1

# Estado detallado con recursos
.\scripts\docker-status.ps1 -Detailed
```

#### Comandos Docker directos
```bash
# Build y deploy
docker-compose up -d --build

# Ver logs
docker-compose logs -f api

# Verificar health checks
docker-compose ps
curl http://localhost:8000/health

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (⚠️ borra datos)
docker-compose down -v
```

### Health Checks

El servicio incluye health checks automáticos:

- **Endpoint**: `GET /health` - Verifica estado de la aplicación y MongoDB
- **Docker Health Check**: Configurado para verificar cada 30 segundos
- **Dependencias**: La API espera a que MongoDB esté saludable antes de iniciar

## 📊 Ejemplos de uso

### Workflow completo
```bash
# 1. Obtener token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token | jq -r .access_token)

# 2. Crear subsecuencias
curl -X POST http://localhost:8000/sequences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"items": [101, 102, 103]}'

# 3. Listar últimas subsecuencias
curl -X GET http://localhost:8000/subsequences \
  -H "Authorization: Bearer $TOKEN"
```

### Casos de uso e-commerce
```python
# Compra de electrónicos
{"items": [2001, 2002, 2003]}  # laptop, mouse, teclado
# Genera recomendaciones de bundles

# Compra recurrente
{"items": [1001, 1001, 1001]}  # café (compra mensual)
# Se deduplica a [1001], en producción usaríamos frecuencia

# Carrito mixto
{"items": [3001, 3002, 3003, 3004, 3005]}  # 5 productos diversos
# Genera 31 subsecuencias para análisis
```

## 🔒 Seguridad

- **JWT Authentication**: Tokens con expiración de 10 minutos
- **Validación de entrada**: IDs positivos, límites de tamaño
- **Rate limiting**: Recomendado para producción
- **Secrets management**: Usar variables de entorno, nunca hardcodear

## 🛠️ Herramientas de desarrollo

### Linting y formateo
```bash
# Formatear código con Black
black app tests

# Linting con Ruff
ruff check app tests --fix

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## 🚀 CI/CD Pipeline

El proyecto incluye pipelines automatizados con GitHub Actions:

### Workflows implementados:

1. **CI (Continuous Integration)**
   - Tests automatizados en Python 3.11 y 3.12
   - Linting con Ruff y Black
   - Coverage mínimo del 70%
   - Análisis de seguridad con Safety y Bandit
   - Ejecuta en cada push y pull request

2. **CD (Continuous Deployment)**
   - Build automático de imágenes Docker
   - Push a GitHub Container Registry
   - Deploy automático a staging (branch `develop`)
   - Deploy automático a producción (tags `v*`)

3. **Security**
   - Revisión de dependencias
   - Análisis de código con CodeQL
   - Escaneo de vulnerabilidades


### Configuración de CI/CD:

Para que los workflows funcionen correctamente:

1. **Variables de entorno en GitHub Secrets:**
   - `MONGODB_URI`: URI de conexión a MongoDB
   - `JWT_SECRET`: Clave secreta para JWT
   - `JWT_ALGORITHM`: Algoritmo JWT (default: HS256)

2. **Permisos del repositorio:**
   - Actions: Read and write permissions
   - Packages: Write permissions (para push de imágenes)

3. **Branch protection rules (recomendado):**
   - Require status checks to pass before merging
   - Require branches to be up to date before merging


