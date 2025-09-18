from __future__ import annotations

import logging
import time
from itertools import combinations
from typing import Iterable

from ..repositories.subsequence_repo import SubsequenceRepository


def canonical_sequence(items: list[int]) -> list[int]:
    """
    Limpia y ordena una secuencia de productos.
    
    Quita duplicados y ordena para evitar problemas con el hash.
    En producción sería mejor guardar las frecuencias, pero para este
    challenge simplificamos.
    """
    return sorted(set(items))

def generate_subsequences(items: list[int]) -> Iterable[list[int]]:
    # Genera todas las combinaciones, primero las más cortas
    n = len(items)
    for k in range(1, n + 1):
        for combo in combinations(items, k):
            yield list(combo)


class SubsequenceService:
    def __init__(self, repo: SubsequenceRepository):
        self.repo = repo
        self.logger = logging.getLogger("app.services.subsequence_service")


    async def create_from_sequence(self, items: list[int]) -> dict:
        canon = canonical_sequence(items)
        n = len(canon)
        if n == 0:
            raise ValueError("La secuencia debe tener al menos un elemento")
        # límite para evitar que se vuelva muy lento
        if n > 18:
            limit_n = 18
            total_subs = 2**limit_n - 1
            raise ValueError(
                f"La secuencia es demasiado grande: n={n} (límite {limit_n}). "
                f"El máximo permitido es {total_subs:,} subsecuencias."
            )

        start = time.perf_counter()
        seq_id = await self.repo.insert_sequence(canon)
        
        # Crear todas las subsecuencias
        subsequences = list(generate_subsequences(canon))
        total_count = len(subsequences)
        
        # Para muchas subsecuencias uso bulk, para pocas inserto una por una
        bulk_threshold = 100
        used_bulk = False
        
        if total_count >= bulk_threshold:
            used_bulk = True
            await self.repo.insert_subsequences_bulk(seq_id, subsequences)
        else:
            for subseq in subsequences:
                await self.repo.upsert_subsequence(seq_id, subseq)
        
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        self.logger.info(
            f"create_from_sequence n_items={n} total_subsequences={total_count} "
            f"used_bulk={used_bulk} duration_ms={duration_ms}"
        )
        return {"id": seq_id, "items": canon, "total_subsequences": total_count}


    async def list_latest(self, limit: int = 10):
        start = time.perf_counter()
        docs = await self.repo.latest_grouped(limit=limit)
        # Ordenar subsecuencias por tamaño y luego alfabéticamente
        for d in docs:
            subs = d["subsequences"]
            subs.sort(key=lambda s: (len(s), s))
            d["sub_sequences"] = subs
            d["sequence"] = d.pop("sequence")
            d.pop("subsequences", None)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        self.logger.info(
            f"list_latest limit={limit} groups={len(docs)} duration_ms={duration_ms}"
        )
        return docs