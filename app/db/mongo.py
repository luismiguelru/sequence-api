import os

from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "seqdb")
COL_SEQ = os.getenv("MONGODB_SEQ_COL", "sequences")
COL_SUB = os.getenv("MONGODB_SUBSEQ_COL", "subsequences")


_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None: #pragma: no cover
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client


async def get_db(): #pragma: no cover
    return get_client()[DB_NAME]


async def ensure_indexes(db): #pragma: no cover
    await db[COL_SEQ].create_index([("created_at", -1)])
    # Unicidad global por hash de items (subsecuencia canonical)
    await db[COL_SUB].create_index("items_hash", unique=True)
    await db[COL_SUB].create_index([("created_at", -1)])
    await db[COL_SUB].create_index("sequence_id")