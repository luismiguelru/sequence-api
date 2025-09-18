import logging
import time

from fastapi import FastAPI, Request

from .api.routes import router
from .db.mongo import ensure_indexes, get_db

app = FastAPI(title="Sequence API")
app.include_router(router)


@app.on_event("startup")
async def on_startup():

    db = await get_db()
    await ensure_indexes(db)


# Configure basic structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
)
logger = logging.getLogger("app")


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    # Minimal structured access log
    user_agent = request.headers.get('user-agent', '')
    logger.info(
        f"request method={request.method} path={request.url.path} "
        f"status={response.status_code} duration_ms={duration_ms} "
        f'ua="{user_agent}"'
    )
    return response