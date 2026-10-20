"""Read-only ledger export endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from node.database import get_db
from node.services.ledger import LedgerService
from node.routes.deps import require_lender

router = APIRouter(tags=["audit ledger"])


@router.get("/v1/ledger/export")
def export_ledger(from_seq: int = Query(default=1, alias="from", ge=1),
                 to_seq: int | None = Query(default=None, alias="to", ge=1),
                 _auth=Depends(require_lender), db: Session = Depends(get_db)):
    if to_seq is not None and to_seq < from_seq:
        raise HTTPException(422, "INVALID_SEQUENCE_RANGE")
    return LedgerService.export(db, from_seq, to_seq)
