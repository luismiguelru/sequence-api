from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from hashlib import sha256

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne
from pymongo.errors import DuplicateKeyError

from ..db.mongo import COL_SEQ, COL_SUB


def _hash_items(items: list[int]) -> str:
    # Crear hash único ordenando los elementos
    key = ",".join(str(x) for x in sorted(items))
    return sha256(key.encode()).hexdigest()




class SubsequenceRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.logger = logging.getLogger("app.repositories.subsequence_repo")


    async def insert_sequence(self, items: list[int]) -> str:
        start = time.perf_counter()
        doc = {
        "items": items,
        "created_at": datetime.now(timezone.utc),
        }
        res = await self.db[COL_SEQ].insert_one(doc)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        self.logger.info(f"insert_sequence size={len(items)} duration_ms={duration_ms}")
        return str(res.inserted_id)


    async def upsert_subsequence(self, sequence_id: str, items: list[int]):
        h = _hash_items(items)
        # Manejar tanto ObjectId como string para sequence_id
        try:
            seq_id_value = ObjectId(sequence_id)
        except Exception:
            seq_id_value = sequence_id  # fallback a string u otro tipo

        doc = {
            "items": sorted(items),
            "items_hash": h,
            "sequence_id": seq_id_value,
            "created_at": datetime.now(timezone.utc),
        }
        # Si ya existe, no hacer nada
        try:
            await self.db[COL_SUB].insert_one(doc)
        except DuplicateKeyError:
            # Ya existe, no pasa nada
            self.logger.debug("upsert_subsequence duplicate ignored items_hash=%s", h)
        except Exception:
            # Re-lanzar otros errores
            raise

    async def insert_subsequences_bulk(
        self, sequence_id: str, subsequences: list[list[int]]
    ) -> int:
        """
        Inserta muchas subsecuencias de una vez.
        Es más rápido que insertar una por una cuando hay muchas.
        """
        if not subsequences:
            return 0
            
        # Usar string para que funcione con los tests
        seq_id_value = sequence_id

        now = datetime.now(timezone.utc)
        operations = []
        
        for items in subsequences:
            h = _hash_items(items)
            doc = {
                "items": sorted(items),
                "items_hash": h,
                "sequence_id": seq_id_value,
                "created_at": now,
            }
            
            # Upsert para no duplicar si ya existe
            operation = UpdateOne(
                {"items_hash": h},  # buscar por hash
                {"$setOnInsert": doc},  # insertar solo si no existe
                upsert=True
            )
            operations.append(operation)
        
        # Ejecutar todas las operaciones de una vez (más rápido)
        start = time.perf_counter()
        result = await self.db[COL_SUB].bulk_write(operations, ordered=False)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        self.logger.info(
            f"insert_subsequences_bulk ops={len(operations)} ordered=False "
            f"duration_ms={duration_ms} upserted={getattr(result,'upserted_count',0)}"
        )
        return result.upserted_count + result.modified_count


    async def latest_grouped(self, limit: int = 10):
        pipeline = [
            # Convertir string a ObjectId para hacer el join
            {
                "$addFields": {
                    "sequence_oid": {"$toObjectId": "$sequence_id"}
                }
            },
            # Agrupar subsecuencias por secuencia original
            {
                "$group": {
                    "_id": "$sequence_id",
                    "subsequences": {"$push": "$items"},
                    "created_at": {"$max": "$created_at"},
                    "sequence_oid": {"$first": "$sequence_oid"}
                }
            },
            # Más recientes primero
            {"$sort": {"created_at": -1}},
            # Solo las primeras N
            {"$limit": limit},
            # Traer los datos de la secuencia original
            {
                "$lookup": {
                    "from": COL_SEQ,
                    "localField": "sequence_oid",
                    "foreignField": "_id",
                    "as": "seq"
                }
            },
            # Sacar la secuencia del array
            {"$unwind": "$seq"},
            # Solo los campos que necesitamos
            {
                "$project": {
                    "sequence": "$seq.items",
                    "subsequences": 1,
                    "_id": 0
                }
            }
        ]
        
        cursor = self.db[COL_SUB].aggregate(pipeline)
        return [doc async for doc in cursor]