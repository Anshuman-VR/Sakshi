"""Decision notice ingestion and SLA clock start."""
import hashlib, re
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from shared.types import DecisionNotice
from node.database import get_db
from node.models import Decision, Policy
from node.routes.deps import require_sidecar
from node.services.policy_engine import parse_iso_datetime

router = APIRouter(tags=["decisions"])
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


@router.post("/v1/decisions", status_code=202)
def create_decision_notice(notice: DecisionNotice, _auth=Depends(require_sidecar), db: Session = Depends(get_db)):
    if not _HEX64.fullmatch(notice.application_id_hash):
        raise HTTPException(422, "INVALID_APPLICATION_ID_HASH")
    if db.get(Decision, notice.decision_id) is not None:
        raise HTTPException(409, "ALREADY_EXISTS")
    policy = db.get(Policy, notice.policy_id)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if policy is None:
        raise HTTPException(400, "POLICY_NOT_FOUND")
    if policy.status == "PENDING" and policy.valid_from <= now <= policy.valid_to:
        policy.status = "ACTIVE"
        db.flush()
    if policy.status == "REVOKED":
        raise HTTPException(400, "POLICY_REVOKED")
    if policy.status == "EXPIRED" or now > policy.valid_to:
        raise HTTPException(400, "POLICY_EXPIRED")
    if now < policy.valid_from or policy.status != "ACTIVE":
        raise HTTPException(400, "POLICY_NOT_YET_VALID")
    try:
        decision_ts = parse_iso_datetime(notice.ts)
    except ValueError:
        raise HTTPException(422, "INVALID_DECISION_TIMESTAMP")
    if decision_ts > now + timedelta(minutes=5):
        raise HTTPException(422, "DECISION_TIMESTAMP_IN_FUTURE")
    decision = Decision(decision_id=notice.decision_id,
        application_id_hash=notice.application_id_hash.lower(), policy_id=notice.policy_id,
        decision=notice.decision, ts=decision_ts, status="NOTICE_RECEIVED",
        sla_deadline=decision_ts + timedelta(minutes=policy.proof_sla_minutes), received_at=now)
    db.add(decision)
    db.commit()
    return {"decision_id": decision.decision_id, "status": decision.status,
            "sla_deadline": decision.sla_deadline.isoformat()}
