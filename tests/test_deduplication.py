import pytest

from app.services.subsequence_service import canonical_sequence, generate_subsequences


class TestDeduplicationBehavior:
    """Tests para verificar que se quitan duplicados correctamente"""
    
    def test_canonical_sequence_removes_duplicates(self):
        """Comprobar que quita duplicados y ordena"""
        # Con duplicados consecutivos
        assert canonical_sequence([1, 2, 2, 3, 1]) == [1, 2, 3]
        
        # Todos duplicados
        assert canonical_sequence([1, 1, 2, 2, 3, 3]) == [1, 2, 3]
        
        # Sin duplicados pero desordenado
        assert canonical_sequence([3, 1, 2]) == [1, 2, 3]
        
        # Un solo elemento repetido
        assert canonical_sequence([5, 5, 5, 5]) == [5]
    
    def test_subsequences_count_with_duplicates(self):
        """Comprobar que el conteo de subsecuencias es correcto"""
        # [1, 2, 2, 3] -> [1, 2, 3] -> 7 subsecuencias (2^3 - 1)
        items = [1, 2, 2, 3]
        canon = canonical_sequence(items)
        assert len(canon) == 3
        subs = list(generate_subsequences(canon))
        assert len(subs) == 7
        
        # [1, 1, 1, 2, 2, 3, 3, 3] -> [1, 2, 3] -> 7 subsecuencias
        items = [1, 1, 1, 2, 2, 3, 3, 3]
        canon = canonical_sequence(items)
        assert len(canon) == 3
        subs = list(generate_subsequences(canon))
        assert len(subs) == 7
    
    def test_frequency_information_lost(self):
        """
        Documenta que la información de frecuencia se pierde.
        En producción, esto podría ser importante para recomendaciones.
        """
        # Cliente que compra mucho producto 2
        heavy_buyer = [1, 2, 2, 2, 2, 3]
        # Cliente que compra poco de cada producto
        light_buyer = [1, 2, 3]
        
        # Ambos generan la misma secuencia canónica
        assert canonical_sequence(heavy_buyer) == canonical_sequence(light_buyer)
        
        # NOTA: En un sistema real, querríamos distinguir estos casos
        # para recomendaciones más precisas (RFM analysis)
    
    def test_real_world_scenarios(self):
        """
        Tests que simulan escenarios del mundo real de e-commerce
        """
        # Escenario 1: Compra de café recurrente (suscripción mensual)
        monthly_coffee = [101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101]
        assert canonical_sequence(monthly_coffee) == [101]
        # En producción: frequency=12 indicaría cliente fiel, ofrecer descuento bulk
        
        # Escenario 2: Compra de electrónicos + accesorios
        electronics_bundle = [200, 201, 201, 202, 202, 202]  # laptop + 2 mouse + 3 cables
        assert canonical_sequence(electronics_bundle) == [200, 201, 202]
        # En producción: las cantidades importarían para bundling
        
        # Escenario 3: Carrito abandonado y recompra
        abandoned_retry = [301, 302, 303, 301, 302, 303]  # intentó comprar 2 veces
        assert canonical_sequence(abandoned_retry) == [301, 302, 303]
        # En producción: detectar patrones de reintento de compra


class TestSubsequenceGeneration:
    """Tests para la generación de subsecuencias"""
    
    def test_subsequences_preserve_order(self):
        """Las subsecuencias mantienen el orden de los elementos originales"""
        items = [1, 2, 3, 4]
        subs = list(generate_subsequences(items))
        
        # Verificar que todas las subsecuencias están ordenadas
        for sub in subs:
            assert sub == sorted(sub)
        
        # Verificar orden: primero por longitud, luego lexicográfico
        assert subs[0:4] == [[1], [2], [3], [4]]  # longitud 1
        assert subs[4:10] == [[1,2], [1,3], [1,4], [2,3], [2,4], [3,4]]  # longitud 2
    
    def test_edge_cases(self):
        """Tests de casos límite"""
        # Un solo elemento
        assert list(generate_subsequences([1])) == [[1]]
        
        # Dos elementos
        assert list(generate_subsequences([1, 2])) == [[1], [2], [1, 2]]
        
        # Verificar cantidad para diferentes tamaños
        for n in range(1, 10):
            items = list(range(1, n + 1))
            subs = list(generate_subsequences(items))
            expected_count = 2**n - 1  # fórmula combinatoria
            assert len(subs) == expected_count, f"Failed for n={n}"


@pytest.mark.parametrize("input_sequence,expected_canonical,expected_sub_count", [
    # Casos del PDF
    ([1], [1], 1),
    ([1, 2], [1, 2], 3),
    ([1, 2, 3], [1, 2, 3], 7),
    ([1, 2, 3, 4], [1, 2, 3, 4], 15),
    
    # Casos con duplicados
    ([1, 1, 1], [1], 1),
    ([2, 1, 2, 1], [1, 2], 3),
    ([3, 3, 2, 2, 1, 1], [1, 2, 3], 7),
    
    # Casos desordenados
    ([4, 3, 2, 1], [1, 2, 3, 4], 15),
    ([10, 5, 15], [5, 10, 15], 7),
])
def test_complete_flow(input_sequence, expected_canonical, expected_sub_count):
    """Test parametrizado que valida el flujo completo"""
    canon = canonical_sequence(input_sequence)
    assert canon == expected_canonical
    
    subs = list(generate_subsequences(canon))
    assert len(subs) == expected_sub_count