"""Dual-signed policy registration and read-only retrieval."""
from datetime import datetime, timezone
import math
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from shared.types import PolicyDocument
from node.database import get_db
from node.models import Policy, RegisteredModel
from node.routes.deps import require_sidecar
from node.services.crypto import canonical_json
from node.services.policy_engine import parse_iso_datetime, validate_policy_signatures, policy_to_document

router = APIRouter(tags=["policies"])
_ALLOWED_OPS = {"eq", "neq", "gte", "lte", "gt", "lt"}


@router.post("/v1/policies", status_code=201)
def register_policy(payload: PolicyDocument, _auth=Depends(require_sidecar), db: Session = Depends(get_db)):
    if db.get(Policy, payload.policy_id) is not None:
        raise HTTPException(409, "ALREADY_EXISTS")
    if not validate_policy_signatures(payload):
        raise HTTPException(400, "INVALID_SIGNATURE")
    if (payload.version < 1 or not payload.policy_id.strip() or not payload.lender_id.strip()
            or not payload.lsp_id.strip() or not payload.product.strip()
            or not math.isfinite(payload.decision_threshold)):
        raise HTTPException(422, "INVALID_POLICY_PARAMETERS")
    model = db.execute(select(RegisteredModel).where(
        RegisteredModel.commitment == payload.model_commitment)).scalar_one_or_none()
    if (model is None or model.status != "APPROVED" or model.revoked_at is not None
            or model.circuit_hash != payload.circuit_hash
            or model.feature_schema_hash != payload.feature_schema_hash):
        raise HTTPException(400, "MODEL_NOT_APPROVED")
    try:
        valid_from = parse_iso_datetime(payload.valid_from)
        valid_to = parse_iso_datetime(payload.valid_to)
    except ValueError:
        raise HTTPException(422, "INVALID_POLICY_VALIDITY")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if valid_to <= valid_from or payload.proof_sla_minutes < 1 or payload.proof_sla_minutes > 1440:
        raise HTTPException(422, "INVALID_POLICY_PARAMETERS")
    if payload.fixed_point_scale <= 0:
        raise HTTPException(422, "INVALID_FIXED_POINT_SCALE")
    for rule in payload.hard_rules:
        if rule.op not in _ALLOWED_OPS or not rule.id.strip() or not rule.feature.strip() or not math.isfinite(rule.value):
            raise HTTPException(422, "INVALID_HARD_RULE")
    canonical_document = payload.model_dump(mode="json", exclude={"lsp_sig", "lender_sig"})
    policy = Policy(policy_id=payload.policy_id, version=payload.version,
        lender_id=payload.lender_id, lsp_id=payload.lsp_id, product=payload.product,
        model_commitment=payload.model_commitment, circuit_hash=payload.circuit_hash,
        feature_schema_hash=payload.feature_schema_hash, decision_threshold=payload.decision_threshold,
        fixed_point_scale=payload.fixed_point_scale,
        hard_rules=[r.model_dump(mode="json") for r in payload.hard_rules],
        proof_sla_minutes=payload.proof_sla_minutes, valid_from=valid_from, valid_to=valid_to,
        lsp_sig=payload.lsp_sig, lender_sig=payload.lender_sig,
        lsp_pubkey=payload.lsp_pubkey, lender_pubkey=payload.lender_pubkey,
        policy_hash=payload.policy_hash(), canonical_document=canonical_document,
        created_at=now, status=("PENDING" if now < valid_from else "EXPIRED" if now > valid_to else "ACTIVE"))
    db.add(policy)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "ALREADY_EXISTS")
    return {"policy_id": policy.policy_id, "version": policy.version,
            "policy_hash": policy.policy_hash, "status": policy.status}


@router.get("/v1/policies/{policy_id}")
def get_policy(policy_id: str, db: Session = Depends(get_db)):
    policy = db.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(404, "POLICY_NOT_FOUND")
    return policy_to_document(policy)
