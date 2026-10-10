from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.retrieval import SearchResponse
from app.services.retrieval import RetrievalService

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str, Query(description="Search text; empty or nonsense returns no results.")] = "",
    k: Annotated[int, Query(ge=1, le=50, description="Max chunks to return.")] = 6,
) -> SearchResponse:
    """Debug endpoint: show the transcript chunks retrieval would return."""
    results = await RetrievalService(db).retrieve(q, k)
    return SearchResponse(query=q, k=k, count=len(results), results=results)
