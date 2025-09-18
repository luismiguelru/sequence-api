from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.repositories.subsequence_repo import SubsequenceRepository, _hash_items
from app.services.subsequence_service import (
    SubsequenceService,
    canonical_sequence,
    generate_subsequences,
)


class TestCanonicalSequence:
    """Tests para la función canonical_sequence"""
    
    def test_basic_canonicalization(self):
        """Test de normalización básica"""
        assert canonical_sequence([3, 1, 2]) == [1, 2, 3]
        assert canonical_sequence([1, 2, 3]) == [1, 2, 3]
        assert canonical_sequence([3, 2, 1]) == [1, 2, 3]
    
    def test_deduplication(self):
        """Test de eliminación de duplicados"""
        assert canonical_sequence([1, 1, 1]) == [1]
        assert canonical_sequence([1, 2, 2, 3]) == [1, 2, 3]
        assert canonical_sequence([5, 3, 5, 1, 3]) == [1, 3, 5]
    
    def test_empty_and_single(self):
        """Test con lista vacía y elemento único"""
        assert canonical_sequence([]) == []
        assert canonical_sequence([42]) == [42]
    
    def test_large_numbers(self):
        """Test con números grandes"""
        large_nums = [1000000, 500000, 2000000, 500000]
        assert canonical_sequence(large_nums) == [500000, 1000000, 2000000]
    
    def test_preserves_type(self):
        """Verifica que el resultado es una lista"""
        result = canonical_sequence([3, 1, 2])
        assert isinstance(result, list)
        assert all(isinstance(x, int) for x in result)


class TestGenerateSubsequences:
    """Tests para la función generate_subsequences"""
    
    def test_single_element(self):
        """Test con un solo elemento"""
        subs = list(generate_subsequences([1]))
        assert subs == [[1]]
    
    def test_two_elements(self):
        """Test con dos elementos"""
        subs = list(generate_subsequences([1, 2]))
        assert subs == [[1], [2], [1, 2]]
    
    def test_three_elements(self):
        """Test con tres elementos (ejemplo del PDF)"""
        subs = list(generate_subsequences([1, 2, 3]))
        expected = [[1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]]
        assert subs == expected
    
    def test_order_preservation(self):
        """Verifica que mantiene el orden: longitud primero, luego lexicográfico"""
        subs = list(generate_subsequences([1, 2, 3, 4]))
        
        # Verificar que están agrupadas por longitud
        lengths = [len(sub) for sub in subs]
        assert lengths == sorted(lengths)
        
        # Verificar orden lexicográfico dentro de cada longitud
        for length in range(1, 5):
            same_length = [s for s in subs if len(s) == length]
            assert same_length == sorted(same_length)
    
    def test_subsequence_count_formula(self):
        """Verifica que genera 2^n - 1 subsecuencias"""
        for n in range(1, 10):
            items = list(range(1, n + 1))
            subs = list(generate_subsequences(items))
            expected_count = 2**n - 1
            assert len(subs) == expected_count
    
    def test_generator_behavior(self):
        """Verifica que es un generador (lazy evaluation)"""
        gen = generate_subsequences([1, 2, 3])
        assert hasattr(gen, '__iter__')
        assert hasattr(gen, '__next__')
        
        # Consumir parcialmente
        first = next(gen)
        assert first == [1]
        second = next(gen)
        assert second == [2]
    
    def test_empty_input(self):
        """Test con entrada vacía"""
        subs = list(generate_subsequences([]))
        assert subs == []


class TestHashFunction:
    """Tests para la función _hash_items del repositorio"""
    
    def test_hash_consistency(self):
        """Verifica que el mismo input produce el mismo hash"""
        items = [1, 2, 3]
        hash1 = _hash_items(items)
        hash2 = _hash_items(items)
        assert hash1 == hash2
    
    def test_hash_order_independence(self):
        """Verifica que el orden no importa para el hash"""
        assert _hash_items([1, 2, 3]) == _hash_items([3, 2, 1])
        assert _hash_items([5, 1, 3]) == _hash_items([1, 3, 5])
    
    def test_hash_uniqueness(self):
        """Verifica que diferentes inputs producen diferentes hashes"""
        hash1 = _hash_items([1, 2, 3])
        hash2 = _hash_items([1, 2, 4])
        hash3 = _hash_items([1, 2])
        
        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3
    
    def test_hash_format(self):
        """Verifica el formato del hash (SHA256 hexadecimal)"""
        hash_val = _hash_items([1, 2, 3])
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64  # SHA256 produce 64 caracteres hex
        assert all(c in '0123456789abcdef' for c in hash_val)


class TestSubsequenceService:
    """Tests para la clase SubsequenceService"""
    
    @pytest.fixture
    def mock_repo(self):
        """Fixture para mock del repositorio"""
        repo = AsyncMock(spec=SubsequenceRepository)
        repo.insert_sequence.return_value = str(ObjectId())
        repo.upsert_subsequence.return_value = None
        repo.latest_grouped.return_value = []
        return repo
    
    @pytest.fixture
    def service(self, mock_repo):
        """Fixture para el servicio con repo mockeado"""
        return SubsequenceService(mock_repo)
    
    @pytest.mark.asyncio
    async def test_create_from_sequence_basic(self, service, mock_repo):
        """Test básico de creación de subsecuencias"""
        items = [1, 2, 3]
        result = await service.create_from_sequence(items)
        
        # Verificar resultado
        assert "id" in result
        assert result["items"] == [1, 2, 3]
        assert result["total_subsequences"] == 7
        
        # Verificar llamadas al repositorio
        mock_repo.insert_sequence.assert_called_once_with([1, 2, 3])
        assert mock_repo.upsert_subsequence.call_count == 7
    
    @pytest.mark.asyncio
    async def test_create_with_duplicates(self, service, mock_repo):
        """Test con elementos duplicados"""
        items = [3, 1, 2, 1, 3]
        result = await service.create_from_sequence(items)
        
        # Debe deduplicar y ordenar
        assert result["items"] == [1, 2, 3]
        assert result["total_subsequences"] == 7
        
        mock_repo.insert_sequence.assert_called_once_with([1, 2, 3])
    
    @pytest.mark.asyncio
    async def test_create_empty_sequence_error(self, service, mock_repo):
        """Test que secuencia vacía lanza error"""
        with pytest.raises(ValueError) as exc_info:
            await service.create_from_sequence([])
        
        assert "al menos un elemento" in str(exc_info.value).lower()
        mock_repo.insert_sequence.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_all_duplicates_single_unique(self, service, mock_repo):
        """Test con todos duplicados resultando en un único elemento"""
        items = [5, 5, 5, 5]
        result = await service.create_from_sequence(items)
        
        assert result["items"] == [5]
        assert result["total_subsequences"] == 1
        
        mock_repo.insert_sequence.assert_called_once_with([5])
        mock_repo.upsert_subsequence.assert_called_once_with(
            mock_repo.insert_sequence.return_value, [5]
        )
    
    @pytest.mark.asyncio
    async def test_create_large_sequence_error(self, service, mock_repo):
        """Test que secuencia muy grande (>18 únicos) lanza error"""
        items = list(range(1, 20))  # 19 elementos únicos
        
        with pytest.raises(ValueError) as exc_info:
            await service.create_from_sequence(items)
        
        error_msg = str(exc_info.value)
        assert "19" in error_msg  # Debe mencionar el número de elementos
        assert "18" in error_msg  # Debe mencionar el límite
        assert "262,143" in error_msg or "262143" in error_msg  # 2^19-1
        
        mock_repo.insert_sequence.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_exactly_18_elements(self, service, mock_repo):
        """Test con exactamente 18 elementos (límite máximo)"""
        items = list(range(1, 19))  # 18 elementos
        result = await service.create_from_sequence(items)
        
        assert result["items"] == list(range(1, 19))
        assert result["total_subsequences"] == 2**18 - 1  # 262,143
        
        mock_repo.insert_sequence.assert_called_once()
        # Con bulk_write habilitado para >=100, no se llamará upsert_subsequence
        # Verificamos que el repositorio fue instruido a usar bulk
        assert mock_repo.insert_subsequences_bulk.called
    
    @pytest.mark.asyncio
    async def test_list_latest_basic(self, service, mock_repo):
        """Test básico de listar últimas subsecuencias"""
        mock_data = [
            {
                "sequence": [1, 2],
                "subsequences": [[2], [1], [1, 2]]  # Desordenadas a propósito
            },
            {
                "sequence": [3, 4, 5],
                "subsequences": [[3], [5], [4], [3, 4], [4, 5], [3, 5], [3, 4, 5]]
            }
        ]
        mock_repo.latest_grouped.return_value = mock_data
        
        result = await service.list_latest(limit=10)
        
        # Verificar que ordena las subsecuencias
        assert result[0]["sequence"] == [1, 2]
        assert result[0]["sub_sequences"] == [[1], [2], [1, 2]]  # Ordenadas
        
        assert result[1]["sequence"] == [3, 4, 5]
        assert result[1]["sub_sequences"] == [
            [3], [4], [5],  # Longitud 1
            [3, 4], [3, 5], [4, 5],  # Longitud 2
            [3, 4, 5]  # Longitud 3
        ]
        
        mock_repo.latest_grouped.assert_called_once_with(limit=10)
    
    @pytest.mark.asyncio
    async def test_list_latest_custom_limit(self, service, mock_repo):
        """Test listar con límite personalizado"""
        mock_repo.latest_grouped.return_value = []
        
        await service.list_latest(limit=5)
        mock_repo.latest_grouped.assert_called_once_with(limit=5)
        
        await service.list_latest(limit=50)
        mock_repo.latest_grouped.assert_called_with(limit=50)
    
    @pytest.mark.asyncio
    async def test_list_latest_empty_result(self, service, mock_repo):
        """Test cuando no hay subsecuencias"""
        mock_repo.latest_grouped.return_value = []
        
        result = await service.list_latest()
        assert result == []
        mock_repo.latest_grouped.assert_called_once_with(limit=10)
    
    @pytest.mark.asyncio
    async def test_subsequence_generation_correctness(self, service, mock_repo):
        """Test que verifica la correctitud de las subsecuencias generadas"""
        test_cases = [
            ([1], 1),
            ([1, 2], 3),
            ([1, 2, 3], 7),
            ([1, 2, 3, 4], 15),
            ([1, 2, 3, 4, 5], 31),
        ]
        
        for items, expected_count in test_cases:
            mock_repo.upsert_subsequence.reset_mock()
            result = await service.create_from_sequence(items)
            
            assert result["total_subsequences"] == expected_count
            assert mock_repo.upsert_subsequence.call_count == expected_count
            
            # Verificar que todas las subsecuencias son únicas
            called_subsequences = [
                call.args[1] 
                for call in mock_repo.upsert_subsequence.call_args_list
            ]
            assert len(called_subsequences) == len(set(map(tuple, called_subsequences)))


class TestSubsequenceRepository:
    """Tests para SubsequenceRepository"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock de la base de datos MongoDB"""
        db = MagicMock()
        
        # Mock de colecciones
        seq_col = AsyncMock()
        sub_col = AsyncMock()
        
        db.__getitem__.side_effect = lambda key: {
            "sequences": seq_col,
            "subsequences": sub_col
        }.get(key, AsyncMock())
        
        return db, seq_col, sub_col
    
    @pytest.fixture
    def repo(self, mock_db):
        """Fixture del repositorio con DB mockeada"""
        db, _, _ = mock_db
        return SubsequenceRepository(db)
    
    @pytest.mark.asyncio
    async def test_insert_sequence(self, repo, mock_db):
        """Test de inserción de secuencia"""
        db, seq_col, _ = mock_db
        
        # Configurar mock
        inserted_id = ObjectId()
        seq_col.insert_one.return_value = AsyncMock(inserted_id=inserted_id)
        
        # Ejecutar
        items = [1, 2, 3]
        result = await repo.insert_sequence(items)
        
        # Verificar
        assert result == str(inserted_id)
        seq_col.insert_one.assert_called_once()
        
        # Verificar estructura del documento
        call_args = seq_col.insert_one.call_args[0][0]
        assert call_args["items"] == items
        assert "created_at" in call_args
        assert isinstance(call_args["created_at"], datetime)
    
    @pytest.mark.asyncio
    async def test_upsert_subsequence(self, repo, mock_db):
        """Test de upsert de subsecuencia"""
        db, _, sub_col = mock_db
        
        sequence_id = str(ObjectId())
        items = [1, 2]
        
        await repo.upsert_subsequence(sequence_id, items)
        
        sub_col.insert_one.assert_called_once()
        
        # Verificar documento
        call_args = sub_col.insert_one.call_args[0][0]
        assert call_args["items"] == [1, 2]  # Ordenados
        assert call_args["items_hash"] == _hash_items(items)
        assert ObjectId(sequence_id) == call_args["sequence_id"]
        assert isinstance(call_args["created_at"], datetime)
    
    @pytest.mark.asyncio
    async def test_upsert_subsequence_duplicate_ignored(self, repo, mock_db):
        """Test que duplicados son ignorados silenciosamente"""
        db, _, sub_col = mock_db
        
        # Simular error de duplicado de manera explícita con DuplicateKeyError
        from pymongo.errors import DuplicateKeyError
        sub_col.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key error")
        
        # No debe propagar la excepción
        try:
            await repo.upsert_subsequence("123", [1, 2])
            exception_raised = False
        except Exception:
            exception_raised = True
        
        assert not exception_raised