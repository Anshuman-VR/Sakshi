"""Dashboard endpoints backed by persisted state and measured values only."""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from shared.types import DashboardSummary, DecisionStatusResponse
from node.database import get_db
from node.models import Decision, LedgerEntry, Policy, RegisteredModel, ProofRecord
from node.services.ledger import LedgerService

router = APIRouter(tags=["dashboard"])


def decision_response(d: Decision) -> DecisionStatusResponse:
    return DecisionStatusResponse(decision_id=d.decision_id, status=d.status,
        decision=d.decision,
        model_commitment=d.model_commitment, policy_id=d.policy_id,
        verified_at=d.verified_at.isoformat() if d.verified_at else None,
        ledger_seq=d.ledger_seq, failure_reason=d.failure_reason,
        sla_deadline=d.sla_deadline.isoformat() if d.sla_deadline else None)


@router.get("/v1/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Decision.status, func.count()).group_by(Decision.status)).all())
    valid, _broken_at = LedgerService.verify_chain(db)
    recent = db.execute(select(Decision).order_by(Decision.received_at.desc()).limit(15)).scalars().all()
    # Derive latency from real persisted timestamps; never report fabricated benchmarks.
    samples = db.execute(select(Decision.received_at, Decision.verified_at).where(
        Decision.verified_at.is_not(None), Decision.status.in_(["VERIFIED", "FAILED"])
    ).order_by(Decision.verified_at.desc()).limit(10000)).all()
    latency_ms = sorted(max(0.0, (end - start).total_seconds() * 1000) for start, end in samples)
    def percentile(p):
        if not latency_ms:
            return None
        return round(latency_ms[min(len(latency_ms) - 1, int((len(latency_ms) - 1) * p))], 3)
    models = db.execute(select(RegisteredModel).where(RegisteredModel.status == "APPROVED")
        .order_by(RegisteredModel.approved_at.desc()).limit(25)).scalars().all()
    policies = db.execute(select(Policy).where(Policy.status == "ACTIVE")
        .order_by(Policy.created_at.desc()).limit(25)).scalars().all()
    return DashboardSummary(total_decisions=sum(int(v) for v in counts.values()),
        verified=int(counts.get("VERIFIED", 0)), failed=int(counts.get("FAILED", 0)),
        pending=int(counts.get("NOTICE_RECEIVED", 0)), expired=int(counts.get("EXPIRED", 0)),
        failure_breakdown=dict(db.execute(select(Decision.failure_reason, func.count()).where(
            Decision.failure_reason.is_not(None)).group_by(Decision.failure_reason)).all()),
        recent_decisions=[decision_response(d) for d in recent],
        proof_latency_p50_ms=percentile(0.50), proof_latency_p95_ms=percentile(0.95),
        ledger_seq=LedgerService.current_sequence(db), chain_valid=valid,
        active_models=[{"id": m.id, "commitment": m.commitment, "status": m.status,
                        "circuit_hash": m.circuit_hash} for m in models],
        active_policies=[{"policy_id": p.policy_id, "policy_hash": p.policy_hash,
                          "status": p.status, "model_commitment": p.model_commitment} for p in policies])


@router.get("/v1/dashboard/decisions")
def dashboard_decisions(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                        status: str | None = Query(None), db: Session = Depends(get_db)):
    query = select(Decision)
    if status:
        query = query.where(Decision.status == status)
    total_query = select(func.count()).select_from(query.subquery())
    total = int(db.execute(total_query).scalar_one())
    rows = db.execute(query.order_by(Decision.received_at.desc()).offset(offset).limit(limit)).scalars().all()
    return {"items": [decision_response(d).model_dump(mode="json") for d in rows],
            "total": total, "limit": limit, "offset": offset}


@router.get("/v1/dashboard/ledger")
def dashboard_ledger(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    rows = db.execute(select(LedgerEntry).order_by(LedgerEntry.seq.desc()).limit(limit)).scalars().all()
    return {"items": [{k: getattr(row, k) for k in (
        "seq", "decision_id", "verification_id", "status", "reason", "policy_id",
        "model_commitment", "proof_hash", "ts", "prev_hash", "row_hash")} for row in rows],
        "total": LedgerService.current_sequence(db)}
