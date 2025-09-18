from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SequenceIn(BaseModel):
    items: list[int] = Field(..., min_length=1, description="IDs de productos (>0)")

    @field_validator('items')
    @classmethod
    def validate_positive_ids(cls, v: list[int]) -> list[int]:
        for idx, item in enumerate(v):
            if item <= 0:
                raise ValueError(f"El ID en posición {idx} debe ser positivo (>0)")
        return v


class SequenceOut(BaseModel):
    id: str = Field(..., description="ID de la secuencia almacenada")
    items: list[int]
    total_subsequences: int


class SubsequenceDoc(BaseModel):
    items: list[int]
    created_at: datetime
    items_hash: str
    sequence_id: str


class SubsequenceListItem(BaseModel):
    sequence: list[int]
    sub_sequences: list[list[int]]