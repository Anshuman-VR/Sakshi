"""Fail-closed decision status endpoint consumed by the LMS."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from shared.types import DecisionStatusResponse
from node.database import get_db
from node.models import Decision
from node.services.sla_monitor import expire_due_decisions

router = APIRouter(tags=["disbursal gate"])


def _response(decision: Decision) -> DecisionStatusResponse:
    return DecisionStatusResponse(decision_id=decision.decision_id, status=decision.status,
        model_commitment=decision.model_commitment, policy_id=decision.policy_id,
        verified_at=decision.verified_at.isoformat() if decision.verified_at else None,
        ledger_seq=decision.ledger_seq, failure_reason=decision.failure_reason,
        sla_deadline=decision.sla_deadline.isoformat() if decision.sla_deadline else None)


@router.get("/v1/decisions/{decision_id}/status", response_model=DecisionStatusResponse)
def gate_status(decision_id: str, db: Session = Depends(get_db)):
    decision = db.get(Decision, decision_id)
    if decision is None:
        return DecisionStatusResponse(decision_id=decision_id, status="NOT_FOUND", failure_reason="NOT_FOUND")
    if decision.status == "NOTICE_RECEIVED" and decision.sla_deadline <= datetime.now(timezone.utc).replace(tzinfo=None):
        db.close()
        expire_due_decisions()
        decision = db.get(Decision, decision_id)
        if decision is None:
            return DecisionStatusResponse(decision_id=decision_id, status="NOT_FOUND", failure_reason="NOT_FOUND")
    # Only VERIFIED is an affirmative authorization. All other values fail closed.
    return _response(decision)
