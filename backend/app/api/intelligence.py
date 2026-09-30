"""
Intelligence API router for Ask MineIntel.
Provides /api/intelligence endpoints aliased with /api/query for clean enterprise routing.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_analyst
from app.schemas.query import QueryRequest, QueryResponse, ClaimVerifyRequest
from app.api.query import execute_query, get_suggestions, verify_claim, get_query_evidence, get_query_calculation

router = APIRouter(prefix="/intelligence", tags=["Ask MineIntel Intelligence"])


@router.post("/query", response_model=QueryResponse)
def intelligence_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """Unified intelligence query endpoint."""
    return execute_query(request=request, db=db, current_user=current_user)


@router.get("/suggestions")
def intelligence_suggestions(
    include_demo: bool = Query(default=False),
    limit: int = Query(default=6, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """Dynamic query suggestions backed by real database facts."""
    return get_suggestions(include_demo=include_demo, limit=limit, db=db, current_user=current_user)


@router.post("/verify-claim")
def intelligence_verify_claim(
    request: ClaimVerifyRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """Verify quantitative mining claim."""
    return verify_claim(request=request, db=db, current_user=current_user)


@router.get("/query/{query_id}/evidence")
def intelligence_query_evidence(
    query_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """Retrieve evidence records used for a specific past query."""
    return get_query_evidence(query_id=query_id, db=db, current_user=current_user)


@router.get("/query/{query_id}/calculation")
def intelligence_query_calculation(
    query_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """Retrieve NumberSafe calculation lineage for a specific past query."""
    return get_query_calculation(query_id=query_id, db=db, current_user=current_user)
