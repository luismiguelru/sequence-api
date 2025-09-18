from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.subsequence_repo import SubsequenceRepository
from app.services.subsequence_service import SubsequenceService


class TestBulkWriteRepository:
    """Tests para el método bulk_write del repositorio"""
    
    @pytest.mark.asyncio
    async def test_insert_subsequences_bulk_empty_list(self):
        """Test que bulk_write maneja lista vacía correctamente"""
        mock_db = MagicMock()
        repo = SubsequenceRepository(mock_db)
        
        result = await repo.insert_subsequences_bulk("seq123", [])
        assert result == 0
        mock_db.__getitem__.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_insert_subsequences_bulk_success(self):
        """Test que bulk_write inserta subsecuencias correctamente"""
        # Mock de la colección con bulk_write
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.upserted_count = 3
        mock_result.modified_count = 0
        mock_collection.bulk_write = AsyncMock(return_value=mock_result)
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        repo = SubsequenceRepository(mock_db)
        subsequences = [[1], [2], [1, 2]]
        
        result = await repo.insert_subsequences_bulk("seq123", subsequences)
        
        assert result == 3
        mock_collection.bulk_write.assert_called_once()
        
        # Verificar que se llamó con ordered=False
        call_args = mock_collection.bulk_write.call_args
        assert call_args[1]['ordered'] is False
        assert len(call_args[0][0]) == 3  # 3 operaciones UpdateOne
    
    @pytest.mark.asyncio
    async def test_insert_subsequences_bulk_operations_structure(self):
        """Test que las operaciones UpdateOne tienen la estructura correcta"""
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.upserted_count = 2
        mock_result.modified_count = 0
        mock_collection.bulk_write = AsyncMock(return_value=mock_result)
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        repo = SubsequenceRepository(mock_db)
        subsequences = [[1], [2]]
        
        await repo.insert_subsequences_bulk("seq123", subsequences)
        
        # Verificar que se crearon operaciones UpdateOne
        call_args = mock_collection.bulk_write.call_args
        operations = call_args[0][0]
        
        assert len(operations) == 2
        for op in operations:
            # UpdateOne de pymongo expone atributos privados
            assert hasattr(op, '_filter')
            assert hasattr(op, '_doc')
            filt = op._filter
            upd = op._doc
            assert 'items_hash' in filt
            assert '$setOnInsert' in upd


class TestBulkWriteService:
    """Tests para el uso de bulk_write en el servicio"""
    
    @pytest.mark.asyncio
    async def test_service_uses_bulk_for_large_sequences(self):
        """Test que el servicio usa bulk_write para secuencias grandes"""
        mock_repo = AsyncMock()
        mock_repo.insert_sequence.return_value = "seq123"
        mock_repo.insert_subsequences_bulk = AsyncMock()
        mock_repo.upsert_subsequence = AsyncMock()
        
        service = SubsequenceService(mock_repo)
        
        # Secuencia que genera más de 100 subsecuencias (n=7 -> 127 subsecuencias)
        large_sequence = list(range(1, 8))  # [1, 2, 3, 4, 5, 6, 7]
        
        result = await service.create_from_sequence(large_sequence)
        
        # Verificar que se usó bulk_write
        mock_repo.insert_subsequences_bulk.assert_called_once()
        mock_repo.upsert_subsequence.assert_not_called()
        
        # Verificar resultado
        assert result["total_subsequences"] == 127  # 2^7 - 1
        assert result["items"] == large_sequence
    
    @pytest.mark.asyncio
    async def test_service_uses_individual_inserts_for_small_sequences(self):
        """Test que el servicio usa inserts individuales para secuencias pequeñas"""
        mock_repo = AsyncMock()
        mock_repo.insert_sequence.return_value = "seq123"
        mock_repo.insert_subsequences_bulk = AsyncMock()
        mock_repo.upsert_subsequence = AsyncMock()
        
        service = SubsequenceService(mock_repo)
        
        # Secuencia pequeña (n=3 -> 7 subsecuencias, menos del umbral de 100)
        small_sequence = [1, 2, 3]
        
        result = await service.create_from_sequence(small_sequence)
        
        # Verificar que se usaron inserts individuales
        mock_repo.upsert_subsequence.assert_called()
        mock_repo.insert_subsequences_bulk.assert_not_called()
        
        # Verificar que se llamó upsert_subsequence 7 veces (2^3 - 1)
        assert mock_repo.upsert_subsequence.call_count == 7
        assert result["total_subsequences"] == 7
    
    @pytest.mark.asyncio
    async def test_service_bulk_threshold_boundary(self):
        """Test el comportamiento en el límite del umbral de bulk"""
        mock_repo = AsyncMock()
        mock_repo.insert_sequence.return_value = "seq123"
        mock_repo.insert_subsequences_bulk = AsyncMock()
        mock_repo.upsert_subsequence = AsyncMock()
        
        service = SubsequenceService(mock_repo)
        
        # Secuencia que genera exactamente 100 subsecuencias (n=7 -> 127, pero forzamos umbral)
        # Para testear el límite, necesitamos una secuencia que genere exactamente 100
        # n=6 -> 63 subsecuencias (menos de 100, usa individual)
        # n=7 -> 127 subsecuencias (más de 100, usa bulk)
        
        # Test con n=6 (debería usar individual)
        small_sequence = list(range(1, 7))  # [1, 2, 3, 4, 5, 6] -> 63 subsecuencias
        result = await service.create_from_sequence(small_sequence)
        
        mock_repo.upsert_subsequence.assert_called()
        mock_repo.insert_subsequences_bulk.assert_not_called()
        assert result["total_subsequences"] == 63


class TestBulkWriteIntegration:
    """Tests de integración para bulk_write con mocks realistas"""
    
    @pytest.mark.asyncio
    async def test_bulk_write_with_fake_collection(self, mock_mongodb):
        """Test que bulk_write funciona con la colección fake de conftest"""
        from app.db.mongo import get_db
        
        db = await get_db()
        repo = SubsequenceRepository(db)
        
        # Insertar una secuencia primero
        seq_id = await repo.insert_sequence([1, 2, 3])
        
        # Usar bulk_write para insertar subsecuencias
        subsequences = [[1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]]
        result = await repo.insert_subsequences_bulk(seq_id, subsequences)
        
        # Verificar que se insertaron las subsecuencias
        assert result == 7
        
        # Verificar que están en la colección fake
        assert len(db["subsequences"]) == 7
        
        # Verificar que las subsecuencias tienen la estructura correcta
        for doc in db["subsequences"]:
            assert "items" in doc
            assert "items_hash" in doc
            assert "sequence_id" in doc
            assert "created_at" in doc
            assert doc["sequence_id"] == seq_id
    
    @pytest.mark.asyncio
    async def test_service_integration_with_bulk(self, mock_mongodb):
        """Test de integración del servicio con bulk_write"""
        from app.db.mongo import get_db
        
        db = await get_db()
        service = SubsequenceService(SubsequenceRepository(db))
        
        # Secuencia que debería usar bulk_write (n=7 -> 127 subsecuencias)
        large_sequence = list(range(1, 8))
        
        result = await service.create_from_sequence(large_sequence)
        
        # Verificar resultado
        assert result["total_subsequences"] == 127
        assert result["items"] == large_sequence
        
        # Verificar que se insertaron en la base de datos fake
        assert len(db["sequences"]) == 1
        assert len(db["subsequences"]) == 127
