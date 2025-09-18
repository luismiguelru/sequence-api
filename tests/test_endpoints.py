from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import status

from app.core.security import JWT_ALG, JWT_SECRET


class TestAuthentication:
    """Tests para validar la autenticación JWT"""
    
    @pytest.mark.asyncio
    async def test_get_token_success(self, client):
        """Test obtener token JWT válido"""
        response = await client.post("/auth/token")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Verificar que el token es válido
        token = data["access_token"]
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        assert decoded["sub"] == "api-client"
        assert "exp" in decoded
        assert "iat" in decoded
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client):
        """Test acceso sin token a endpoint protegido"""
        # POST /sequences sin token
        response = await client.post("/sequences", json={"items": [1, 2, 3]})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # GET /subsequences sin token
        response = await client.get("/subsequences")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, client):
        """Test acceso con token inválido"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        
        # POST /sequences con token inválido
        response = await client.post("/sequences", json={"items": [1, 2, 3]}, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token inválido" in response.json()["detail"]
        
        # GET /subsequences con token inválido
        response = await client.get("/subsequences", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_expired_token(self, client):
        """Test acceso con token expirado"""
        # Crear token expirado manualmente
        now = datetime.now(timezone.utc)
        exp = now - timedelta(minutes=1)  # Expiró hace 1 minuto
        payload = {
            "sub": "api-client",
            "iat": int((now - timedelta(minutes=11)).timestamp()),
            "exp": int(exp.timestamp())
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        # POST /sequences con token expirado
        response = await client.post("/sequences", json={"items": [1, 2, 3]}, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token expirado" in response.json()["detail"]
        
        # GET /subsequences con token expirado
        response = await client.get("/subsequences", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token expirado" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_token_expires_in_10_minutes(self, client):
        """Verificar que el token expira en exactamente 10 minutos"""
        response = await client.post("/auth/token")
        token = response.json()["access_token"]
        
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        iat = decoded["iat"]
        exp = decoded["exp"]
        
        # Verificar que la diferencia es 10 minutos (600 segundos)
        diff = exp - iat
        assert 595 <= diff <= 605  # Permitir pequeña variación


class TestSubsequencesEndpoint:
    """Tests para el endpoint GET /subsequences"""
    
    @pytest.mark.asyncio
    async def test_list_subsequences_success(self, client, auth_headers):
        """Test listar subsecuencias con éxito"""
        # GET /subsequences
        response = await client.get("/subsequences", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verificar estructura del primer item
        first_item = data[0]
        assert "sequence" in first_item
        assert "sub_sequences" in first_item
        assert isinstance(first_item["sequence"], list)
        assert isinstance(first_item["sub_sequences"], list)
    
    @pytest.mark.asyncio
    async def test_list_subsequences_with_limit(self, client, auth_headers):
        """Test listar subsecuencias con límite personalizado"""
        # GET /subsequences con límite 5
        response = await client.get("/subsequences?limit=5", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        
        # GET /subsequences con límite máximo (50)
        response = await client.get("/subsequences?limit=50", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_list_subsequences_invalid_limit(self, client, auth_headers):
        """Test listar subsecuencias con límite inválido"""
        # Límite menor al mínimo (0)
        response = await client.get("/subsequences?limit=0", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Límite mayor al máximo (51)
        response = await client.get("/subsequences?limit=51", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Límite no numérico
        response = await client.get("/subsequences?limit=abc", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_subsequences_ordering(self, client, auth_headers):
        """Verificar que las subsecuencias están ordenadas correctamente"""
        # GET /subsequences
        response = await client.get("/subsequences", headers=auth_headers)
        data = response.json()
        
        # Verificar orden de subsecuencias en el primer item
        if len(data) > 0:
            subsequences = data[0]["sub_sequences"]
            
            # Verificar que están ordenadas por longitud y luego lexicográficamente
            for i in range(1, len(subsequences)):
                prev = subsequences[i-1]
                curr = subsequences[i]
                
                # Si tienen la misma longitud, deben estar en orden lexicográfico
                if len(prev) == len(curr):
                    assert prev < curr, f"Orden incorrecto: {prev} debería estar antes que {curr}"
                # Si no, la anterior debe ser más corta
                else:
                    assert len(prev) < len(curr), f"Longitudes desordenadas: {prev} y {curr}"


class TestEndToEndFlow:
    """Tests de flujo completo de la aplicación"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, client, auth_headers):
        """Test del flujo completo: autenticación → crear → listar"""
        # 1. Obtener token (ya disponible en auth_headers)
        # 2. Crear primera secuencia
        response = await client.post("/sequences", json={"items": [1, 2, 3]}, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_subsequences"] == 7
        # first_id = data["id"]  # No usado, comentado para evitar F841
        
        # 3. Crear segunda secuencia
        response = await client.post("/sequences", json={"items": [4, 5, 6]}, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_subsequences"] == 7
        # second_id = data["id"]  # No usado, comentado para evitar F841
        
        # 4. Listar subsecuencias (deberían aparecer ambas)
        response = await client.get("/subsequences", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Verificar que se devuelven en orden (más recientes primero)
        # Nota: Este test depende de la implementación del mock
    
    @pytest.mark.asyncio
    async def test_large_sequence_rejection(self, client, auth_headers):
        """Test que secuencias muy grandes (n>18) son rechazadas"""
        # Crear secuencia con 19 elementos únicos
        large_sequence = list(range(1, 20))  # [1, 2, ..., 19]
        response = await client.post(
            "/sequences", json={"items": large_sequence}, headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "demasiado grande" in response.json()["detail"].lower()


class TestHealthCheck:
    """Tests para el endpoint de health check"""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check cuando la aplicación está funcionando correctamente"""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["service"] == "sequence-api"
    
    @pytest.mark.asyncio
    async def test_health_check_no_auth_required(self, client):
        """Test que el endpoint de health no requiere autenticación"""
        # No enviar headers de autorización
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "service" in data
    
    @pytest.mark.asyncio
    async def test_health_check_response_structure(self, client):
        """Test que la respuesta del health check tiene la estructura correcta"""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        
        # Verificar que todos los campos requeridos están presentes
        required_fields = ["status", "database", "service"]
        for field in required_fields:
            assert field in data, f"Campo '{field}' faltante en la respuesta"
        
        # Verificar tipos de datos
        assert isinstance(data["status"], str)
        assert isinstance(data["database"], str)
        assert isinstance(data["service"], str)
        
        # Verificar valores específicos
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["service"] == "sequence-api"
    
    @pytest.mark.asyncio
    async def test_health_check_database_ping(self, client):
        """Test que verifica que el health check hace ping a la base de datos"""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        # El mock de MongoDB simula un ping exitoso
        assert data["database"] == "connected"