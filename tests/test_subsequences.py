import pytest
from fastapi import status

from app.services.subsequence_service import canonical_sequence, generate_subsequences


@pytest.mark.asyncio
async def test_token_and_flow(client, auth_headers):
    r = await client.post("/sequences", json={"items": [1, 2, 3]}, headers=auth_headers)
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert data["total_subsequences"] == 7


@pytest.mark.asyncio
async def test_negative_ids_validation(client, auth_headers):
    """Test que valida que los IDs deben ser positivos"""
    # Test con ID negativo
    r = await client.post("/sequences", json={"items": [1, -2, 3]}, headers=auth_headers)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = r.json()
    assert "debe ser positivo" in error["detail"][0]["msg"]
    
    # Test con cero
    r = await client.post("/sequences", json={"items": [0, 1, 2]}, headers=auth_headers)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Test con todos negativos
    r = await client.post("/sequences", json={"items": [-1, -2, -3]}, headers=auth_headers)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_empty_sequence_validation(client, auth_headers):
    """Test que valida que la secuencia no puede estar vacía"""
    # Test con lista vacía
    r = await client.post("/sequences", json={"items": []}, headers=auth_headers)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("inp,canon", [
    ([3,1,2,2], [1,2,3]),
    ([5,5,5], [5]),
])
def test_canonical_sequence(inp, canon):
    assert canonical_sequence(inp) == canon


def test_generate_subsequences_order():
    items = [1,2,3]
    subs = list(generate_subsequences(items))
    assert subs == [[1],[2],[3],[1,2],[1,3],[2,3],[1,2,3]]