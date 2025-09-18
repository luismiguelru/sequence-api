import asyncio
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import status

from app.core.security import JWT_ALG, JWT_EXPIRE_MIN, JWT_SECRET, create_access_token


class TestJWTToken:
    """Tests unitarios para la generación y validación de tokens JWT"""
    
    def test_create_access_token_structure(self):
        """Verifica que el token generado tiene la estructura correcta"""
        token = create_access_token()
        
        # Verificar que es un string no vacío
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verificar que tiene 3 partes (header.payload.signature)
        parts = token.split('.')
        assert len(parts) == 3
    
    def test_token_payload_content(self):
        """Verifica el contenido del payload del token"""
        token = create_access_token()
        
        # Decodificar sin verificar expiración para inspeccionar
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        
        # Verificar campos requeridos
        assert decoded["sub"] == "api-client"
        assert "iat" in decoded  # issued at
        assert "exp" in decoded  # expiration
        
        # Verificar tipos
        assert isinstance(decoded["iat"], int)
        assert isinstance(decoded["exp"], int)
    
    def test_token_expiration_time(self):
        """Verifica que el token expira en el tiempo configurado"""
        token = create_access_token()
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        
        iat = decoded["iat"]
        exp = decoded["exp"]
        
        # La diferencia debe ser JWT_EXPIRE_MIN minutos (en segundos)
        expected_diff = JWT_EXPIRE_MIN * 60
        actual_diff = exp - iat
        
        # Permitir pequeña variación (±5 segundos)
        assert abs(actual_diff - expected_diff) <= 5
    
    def test_token_algorithm(self):
        """Verifica que el token usa el algoritmo configurado"""
        token = create_access_token()
        
        # Decodificar header sin verificación
        import base64
        import json
        header_data = token.split('.')[0]
        # Agregar padding si es necesario
        header_data += '=' * (4 - len(header_data) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_data))
        
        assert header["alg"] == JWT_ALG
        assert header["typ"] == "JWT"
    
    def test_token_validation_with_correct_secret(self):
        """Verifica que el token se valida correctamente con el secret correcto"""
        token = create_access_token()
        
        # No debe lanzar excepción
        try:
            jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            validation_passed = True
        except jwt.InvalidTokenError:
            validation_passed = False
        
        assert validation_passed
    
    def test_token_validation_with_wrong_secret(self):
        """Verifica que el token falla con un secret incorrecto"""
        token = create_access_token()
        
        # Debe lanzar excepción con secret incorrecto
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=[JWT_ALG])
    
    def test_token_validation_with_wrong_algorithm(self):
        """Verifica que el token falla con algoritmo incorrecto"""
        token = create_access_token()
        
        # Debe lanzar excepción con algoritmo incorrecto
        with pytest.raises(jwt.InvalidAlgorithmError):
            jwt.decode(token, JWT_SECRET, algorithms=["RS256"])  # Diferente algoritmo
    
    def test_expired_token_validation(self):
        """Verifica que un token expirado es rechazado"""
        # Crear token que ya expiró
        now = datetime.now(timezone.utc)
        exp = now - timedelta(seconds=1)  # Expiró hace 1 segundo
        payload = {
            "sub": "api-client",
            "iat": int((now - timedelta(minutes=11)).timestamp()),
            "exp": int(exp.timestamp())
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
        
        # Debe lanzar excepción de token expirado
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, JWT_SECRET, algorithms=[JWT_ALG])
    
    def test_malformed_token_validation(self):
        """Verifica que tokens malformados son rechazados"""
        malformed_tokens = [
            "not.a.token",
            "invalid",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Solo header
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",  # Sin signature
        ]
        
        for bad_token in malformed_tokens:
            with pytest.raises(jwt.InvalidTokenError):
                jwt.decode(bad_token, JWT_SECRET, algorithms=[JWT_ALG])




class TestAuthEndpoint:
    """Tests del endpoint /auth/token"""
    
    @pytest.mark.asyncio
    async def test_token_endpoint_success(self, client):
        """Test exitoso de obtención de token"""
        response = await client.post("/auth/token")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_token_endpoint_response_format(self, client):
        """Verifica el formato de la respuesta del endpoint"""
        response = await client.post("/auth/token")
        data = response.json()
        
        # Verificar que solo tiene los campos esperados
        assert set(data.keys()) == {"access_token", "token_type"}
        
        # Verificar tipos
        assert isinstance(data["access_token"], str)
        assert isinstance(data["token_type"], str)
        
        # Verificar que el token no está vacío
        assert len(data["access_token"]) > 0
    
    @pytest.mark.asyncio
    async def test_token_endpoint_method_not_allowed(self, client):
        """Verifica que otros métodos HTTP no están permitidos"""
        # GET no debería funcionar
        response = await client.get("/auth/token")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        
        # PUT no debería funcionar
        response = await client.put("/auth/token")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        
        # DELETE no debería funcionar
        response = await client.delete("/auth/token")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    @pytest.mark.asyncio
    async def test_token_endpoint_no_body_required(self, client):
        """Verifica que el endpoint no requiere body"""
        # Con body vacío
        response = await client.post("/auth/token", json={})
        assert response.status_code == status.HTTP_200_OK
        
        # Con body arbitrario (debe ignorarse)
        response = await client.post("/auth/token", json={"foo": "bar"})
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_token_uniqueness(self, client):
        """Verifica que cada token generado es único"""
        tokens = []
        
        # Generar varios tokens
        for _ in range(5):
            response = await client.post("/auth/token")
            token = response.json()["access_token"]
            tokens.append(token)
            
            # Pequeña pausa para asegurar diferentes timestamps
            await asyncio.sleep(0.1)
        
        # Todos deben ser únicos
        assert len(tokens) == len(set(tokens))
    
    @pytest.mark.asyncio
    async def test_token_can_be_decoded(self, client):
        """Verifica que el token del endpoint puede ser decodificado"""
        response = await client.post("/auth/token")
        token = response.json()["access_token"]
        
        # Debe poder decodificarse sin errores
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            assert decoded["sub"] == "api-client"
            decode_success = True
        except jwt.InvalidTokenError:
            decode_success = False
        
        assert decode_success
    
    @pytest.mark.asyncio
    async def test_concurrent_token_generation(self, client):
        """Verifica que múltiples requests concurrentes funcionan correctamente"""
        import asyncio
        
        async def get_token():
            response = await client.post("/auth/token")
            return response.json()["access_token"]
        
        # Generar 10 tokens concurrentemente
        tokens = await asyncio.gather(*[get_token() for _ in range(10)])
        
        # Todos deben ser válidos
        for token in tokens:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            assert decoded["sub"] == "api-client"
        
        # Todos deben ser únicos (diferentes iat)
        assert len(tokens) == len(set(tokens))


class TestTokenUsageInEndpoints:
    """Tests de uso de tokens en endpoints protegidos"""
    
    @pytest.mark.asyncio
    async def test_valid_token_grants_access(self, client, monkeypatch):
        """Verifica que un token válido permite acceso"""
        # Usar token válido a través del fixture
        token_response = await client.post("/auth/token")
        token = token_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/sequences",
            json={"items": [1, 2, 3]},
            headers=headers
        )
        
        # Debe permitir acceso
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
    
    @pytest.mark.asyncio
    async def test_invalid_bearer_format(self, client):
        """Verifica que formatos incorrectos de Bearer son rechazados"""
        invalid_headers = [
            {"Authorization": "Bearer"},  # Sin token
            {"Authorization": "Bearer  "},  # Token vacío
            {"Authorization": "Token abc123"},  # Esquema incorrecto
            {"Authorization": "bearer abc123"},  # Minúscula
            {"Authorization": "Bearertoken123"},  # Sin espacio
        ]
        
        for headers in invalid_headers:
            response = await client.get("/subsequences", headers=headers)
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN
            ]
    
    @pytest.mark.asyncio
    async def test_token_in_different_endpoints(self, client, monkeypatch):
        """Verifica que el mismo token funciona en múltiples endpoints"""
        # Obtener token una vez
        token_response = await client.post("/auth/token")
        token = token_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Probar en POST /sequences
        response = await client.post(
            "/sequences",
            json={"items": [1, 2, 3]},
            headers=headers
        )
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        
        # Probar en GET /subsequences
        response = await client.get("/subsequences", headers=headers)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED