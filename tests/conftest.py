"""
Fixtures y configuración para los tests.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator

# Configurar variables de entorno antes de importar módulos que las usan
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from bson import ObjectId
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def patch_motor_client(monkeypatch):
    # Configurar JWT para los tests
    monkeypatch.setenv("JWT_SECRET", os.environ.get("JWT_SECRET", "test-secret"))
    # Stub básico por si algo usa el cliente real antes del mock
    class _MinimalCollection(list):
        def __init__(self, name=""):
            super().__init__()
            self.name = name
        async def insert_one(self, document):
            from bson import ObjectId
            doc = dict(document)
            if "_id" not in doc:
                doc["_id"] = ObjectId()
            self.append(doc)
            class _Res:
                def __init__(self, _id):
                    self.inserted_id = _id
            return _Res(doc["_id"])

        async def create_index(self, *_, **__):
            return None

        def aggregate(self, _pipeline):
            class _AsyncCursor:
                def __init__(self, data):
                    self._data = data
                    self._i = 0
                def __aiter__(self):
                    return self
                async def __anext__(self):
                    if self._i >= len(self._data):
                        raise StopAsyncIteration
                    item = self._data[self._i]
                    self._i += 1
                    return item
            # Datos de ejemplo para subsequences
            if getattr(self, "name", "") == "subsequences":
                data = [
                    {
                        "sequence": [1, 2, 3],
                        "subsequences": [[1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]],
                    },
                    {
                        "sequence": [4, 5],
                        "subsequences": [[4], [5], [4, 5]],
                    },
                ]
                return _AsyncCursor(data)
            # Devuelve cursor vacío por defecto
            return _AsyncCursor([])

    class DummyDB(dict):
        def __getitem__(self, k):
            if k not in self:
                self[k] = _MinimalCollection(name=k)
            return super().__getitem__(k)

    class DummyClient:
        def __getitem__(self, name):
            return DummyDB()
    monkeypatch.setattr("app.db.mongo.AsyncIOMotorClient",
                        lambda *a, **k: DummyClient())


# Configuración para tests async
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client(mock_mongodb) -> AsyncGenerator:
    """Cliente HTTP async para tests de endpoints."""
    # Importar la app después de aplicar los mocks asegura que `app.main`
    # resuelva `get_db/ensure_indexes` ya parcheados.
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Headers con token JWT válido para tests de endpoints protegidos."""
    response = await client.post("/auth/token")
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_mongodb(monkeypatch):
    """
    Mock completo de MongoDB para tests.
    Simula las colecciones sequences y subsequences.
    """
    class FakeDocument(dict):
        """Simula un documento MongoDB con _id"""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if "_id" not in self:
                self["_id"] = ObjectId()
    
    class FakeCollection(list):
        """Simula una colección MongoDB"""
        def __init__(self, name=""):
            super().__init__()
            self.name = name
            self.indexes = []
        
        async def insert_one(self, document):
            """Simula insert_one de MongoDB"""
            doc = FakeDocument(document)
            if "_id" not in doc:
                doc["_id"] = ObjectId()
            self.append(doc)
            
            class InsertResult:
                def __init__(self, inserted_id):
                    self.inserted_id = inserted_id
            
            return InsertResult(doc["_id"])
        
        async def find_one(self, filter_dict):
            """Simula find_one de MongoDB"""
            for doc in self:
                if all(doc.get(k) == v for k, v in filter_dict.items()):
                    return doc
            return None
        
        async def find(self, filter_dict=None):
            """Simula find de MongoDB"""
            if filter_dict is None:
                return self
            
            results = []
            for doc in self:
                if all(doc.get(k) == v for k, v in filter_dict.items()):
                    results.append(doc)
            return results
        
        async def create_index(self, keys, **kwargs):
            """Simula create_index de MongoDB"""
            self.indexes.append({"keys": keys, "options": kwargs})
            return f"index_{len(self.indexes)}"
        
        async def bulk_write(self, operations, ordered=False):
            """Simula bulk_write de MongoDB"""
            class BulkWriteResult:
                def __init__(self, ops_count):
                    self.upserted_count = ops_count
                    self.modified_count = 0
                    self.inserted_count = 0
                    self.matched_count = 0
                    self.deleted_count = 0
            
            # Simular procesamiento de operaciones UpdateOne
            processed_count = 0
            for op in operations:
                # Soporte para UpdateOne de pymongo
                if hasattr(op, '_filter') and hasattr(op, '_doc'):
                    filter_dict = op._filter
                    update_dict = op._doc
                    # Verificar existencia por filtro exacto
                    exists = any(
                        all(doc.get(k) == v for k, v in filter_dict.items()) 
                        for doc in self
                    )
                    if not exists and '$setOnInsert' in update_dict:
                        new_doc = update_dict['$setOnInsert'].copy()
                        if '_id' not in new_doc:
                            new_doc['_id'] = ObjectId()
                        self.append(new_doc)
                        processed_count += 1
                else:
                    # Otras operaciones (InsertOne, etc.)
                    processed_count += 1
            
            return BulkWriteResult(processed_count)
        
        def aggregate(self, pipeline):
            """Simula aggregate de MongoDB"""
            # Simulación básica para tests
            class AsyncCursor:
                def __init__(self, data):
                    self.data = data
                    self.index = 0
                
                def __aiter__(self):
                    return self
                
                async def __anext__(self):
                    if self.index >= len(self.data):
                        raise StopAsyncIteration
                    item = self.data[self.index]
                    self.index += 1
                    return item
            
            # Datos de prueba para aggregate
            test_data = [
                {
                    "sequence": [1, 2, 3],
                    "subsequences": [[1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]]
                },
                {
                    "sequence": [4, 5],
                    "subsequences": [[4], [5], [4, 5]]
                }
            ]
            return AsyncCursor(test_data)
    
    class FakeDB(dict):
        """Simula una base de datos MongoDB"""
        def __init__(self):
            super().__init__()
            self["sequences"] = FakeCollection("sequences")
            self["subsequences"] = FakeCollection("subsequences")
        
        def __getitem__(self, key):
            if key not in self:
                self[key] = FakeCollection(key)
            return super().__getitem__(key)
        
        async def command(self, command):
            """Simula el comando ping de MongoDB para health checks"""
            if command == "ping":
                return {"ok": 1.0}
            raise Exception(f"Comando no soportado: {command}")
    
    # Patchear las funciones de mongo.py
    from app.db import mongo as mongo_mod
    
    fake_db = FakeDB()
    
    async def fake_get_db():
        return fake_db
    
    async def fake_ensure_indexes(db):
        """Simula la creación de índices"""
        await db["sequences"].create_index([("created_at", -1)])
        await db["subsequences"].create_index("items_hash", unique=True)
        await db["subsequences"].create_index([("created_at", -1)])
        await db["subsequences"].create_index("sequence_id")
    
    monkeypatch.setattr(mongo_mod, "get_db", fake_get_db)
    monkeypatch.setattr(mongo_mod, "ensure_indexes", fake_ensure_indexes)
    
    # Si `app.main` ya fue importado en algún test, parchear sus referencias directas
    try:
        import app.main as app_main
        monkeypatch.setattr(app_main, "get_db", fake_get_db, raising=False)
        monkeypatch.setattr(app_main, "ensure_indexes", fake_ensure_indexes, raising=False)
    except Exception:
        pass

    # Si `app.api.routes` ya fue importado, parchear su referencia a get_db
    try:
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "get_db", fake_get_db, raising=False)
    except Exception:
        pass
    
    return fake_db


@pytest.fixture
def sample_sequences():
    """Secuencias de ejemplo para tests."""
    return {
        "simple": [1, 2, 3],
        "with_duplicates": [1, 2, 2, 3, 1],
        "single": [42],
        "empty": [],
        "large": list(range(1, 19)),  # 18 elementos (límite)
        "too_large": list(range(1, 20)),  # 19 elementos (sobre el límite)
        "unordered": [5, 2, 8, 1, 3],
    }


@pytest.fixture
def expected_subsequences():
    """Subsecuencias esperadas para las secuencias de ejemplo."""
    return {
        "simple": [
            [1], [2], [3],
            [1, 2], [1, 3], [2, 3],
            [1, 2, 3]
        ],
        "single": [[42]],
        "empty": [],
    }