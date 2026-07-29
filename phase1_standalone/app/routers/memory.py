from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import schemas
from app.memory_engine import store as memory_store

router = APIRouter(prefix="/api/v1", tags=["memory"])


@router.get("/memory/search", response_model=List[schemas.MemoryOut])
def search_memory(q: str = Query(...), k: int = Query(5, ge=1, le=50), db: Session = Depends(get_db)):
    return memory_store.search_memories(db, q, k=k)
