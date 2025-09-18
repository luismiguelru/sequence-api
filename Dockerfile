# Multi-stage build para optimizar cache y tamaño
FROM python:3.11-slim AS builder

# Instalar dependencias del sistema necesarias para compilar
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias en directorio temporal
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage final - imagen más pequeña
FROM python:3.11-slim

# Instalar solo curl para health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias instaladas desde builder
COPY --from=builder /root/.local /root/.local

# Configurar PATH para usar dependencias instaladas
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

# Copiar código de la aplicación
COPY app ./app
COPY pyproject.toml pre-commit-config.yaml ./

# Variables de entorno optimizadas
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Exponer puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]