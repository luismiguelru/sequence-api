from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.security import create_access_token, jwt_guard
from ..db.mongo import get_db
from ..models.schemas import SequenceIn, SequenceOut, SubsequenceListItem
from ..repositories.subsequence_repo import SubsequenceRepository
from ..services.subsequence_service import SubsequenceService

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check(db=Depends(get_db)):
    """
    Health check endpoint para verificar el estado de la aplicación y MongoDB.
    """
    try:
        # Verificar conexión a MongoDB
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "service": "sequence-api"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "service": "sequence-api",
                "error": str(e)
            }
        ) from e


@router.post("/auth/token", tags=["auth"])
def issue_token():
    return {"access_token": create_access_token(), "token_type": "bearer"}


@router.post(
    "/sequences",
    response_model=SequenceOut,
    dependencies=[Depends(jwt_guard)],
    tags=["sequences"],
)
async def create_sequences(payload: SequenceIn, db=Depends(get_db)):
    service = SubsequenceService(SubsequenceRepository(db))
    try:
        result = await service.create_from_sequence(payload.items)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get(
    "/subsequences",
    response_model=List[SubsequenceListItem],
    dependencies=[Depends(jwt_guard)],
    tags=["subsequences"],
)
async def list_subsequences(
    limit: int = Query(10, ge=1, le=50), 
    db=Depends(get_db)
):
    service = SubsequenceService(SubsequenceRepository(db))
    return await service.list_latest(limit=limit)