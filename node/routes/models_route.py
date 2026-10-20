"""Model registry and explicit lender approval endpoints."""
import json, uuid, math, re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from shared.types import ModelRegistration
from node.config import config
from node.database import get_db
from node.models import RegisteredModel, Policy
from node.routes.deps import require_sidecar, require_lender
from node.services.crypto import decode_b64, lender_approval_payload, verify_ed25519
from node.services.policy_engine import model_public, validate_model_registration

router = APIRouter(tags=["model registry"])


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lender_sig: str = Field(min_length=1)
    lender_pubkey: str = Field(min_length=64, max_length=128)


@router.post("/v1/models", status_code=status.HTTP_201_CREATED)
def register_model(payload: ModelRegistration, _auth=Depends(require_sidecar), db: Session = Depends(get_db)):
    if db.execute(select(RegisteredModel.id).where(RegisteredModel.commitment == payload.commitment)).first():
        raise HTTPException(409, "ALREADY_REGISTERED")
    def valid_hash(value: str) -> bool:
        value = value.removeprefix("0x").removeprefix("0X")
        return len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)
    if not all(valid_hash(v) for v in (payload.commitment, payload.circuit_hash, payload.feature_schema_hash)):
        raise HTTPException(422, "INVALID_MODEL_HASH")
    try:
        vk_bytes = decode_b64(payload.vk)
        vk_json = json.loads(vk_bytes.decode("utf-8"))
        if not isinstance(vk_json, (dict, list)) or not vk_bytes:
            raise ValueError("invalid verification key")
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(400, "INVALID_VERIFICATION_KEY")
    if not validate_model_registration(payload):
        raise HTTPException(400, "INVALID_SIGNATURE")
    parity = payload.parity_report
    try:
        agreement = float(parity["agreement_pct"])
        float_auc = float(parity["float_auc"])
        quantized_auc = float(parity["quantized_auc"])
        samples = int(parity["test_samples"])
        if (not math.isfinite(agreement) or not 0 <= agreement <= 100
                or not math.isfinite(float_auc) or not 0 <= float_auc <= 1
                or not math.isfinite(quantized_auc) or not 0 <= quantized_auc <= 1
                or samples <= 0):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise HTTPException(400, "INVALID_PARITY_REPORT")
    model = RegisteredModel(id=f"m_{uuid.uuid4().hex}", commitment=payload.commitment,
        circuit_hash=payload.circuit_hash, vk=payload.vk,
        feature_schema_hash=payload.feature_schema_hash, parity_report=parity,
        lsp_sig=payload.lsp_sig, lsp_pubkey=payload.lsp_pubkey, status="PENDING_APPROVAL")
    db.add(model)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "ALREADY_REGISTERED")
    db.refresh(model)
    return {"model_id": model.id, "status": model.status, "commitment": model.commitment}


@router.post("/v1/models/{model_id}/approve")
def approve_model(model_id: str, payload: ApprovalRequest, _auth=Depends(require_lender), db: Session = Depends(get_db)):
    model = db.get(RegisteredModel, model_id)
    if model is None:
        raise HTTPException(404, "NOT_FOUND")
    if model.status != "PENDING_APPROVAL":
        raise HTTPException(409, "INVALID_MODEL_STATE")
    if config.lender_pubkey and payload.lender_pubkey.lower() != config.lender_pubkey.lower():
        raise HTTPException(400, "INVALID_SIGNATURE")
    if not verify_ed25519(payload.lender_pubkey, payload.lender_sig,
                          lender_approval_payload(model.id, model.commitment, circuit_hash=model.circuit_hash, feature_schema_hash=model.feature_schema_hash)):
        raise HTTPException(400, "INVALID_SIGNATURE")
    model.status = "APPROVED"
    model.lender_sig = payload.lender_sig
    model.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"model_id": model.id, "status": model.status, "approved_at": model.approved_at.isoformat()}


@router.post("/v1/models/{model_id}/reject")
def reject_model(model_id: str, payload: ApprovalRequest, _auth=Depends(require_lender), db: Session = Depends(get_db)):
    model = db.get(RegisteredModel, model_id)
    if model is None:
        raise HTTPException(404, "NOT_FOUND")
    if model.status != "PENDING_APPROVAL":
        raise HTTPException(409, "INVALID_MODEL_STATE")
    if config.lender_pubkey and payload.lender_pubkey.lower() != config.lender_pubkey.lower():
        raise HTTPException(400, "INVALID_SIGNATURE")
    if not verify_ed25519(payload.lender_pubkey, payload.lender_sig,
                          lender_approval_payload(model.id, model.commitment, "REJECT", model.circuit_hash, model.feature_schema_hash)):
        raise HTTPException(400, "INVALID_SIGNATURE")
    model.status = "REJECTED"
    model.lender_sig = payload.lender_sig
    db.commit()
    return {"model_id": model.id, "status": model.status}


@router.post("/v1/models/{model_id}/revoke")
def revoke_model(model_id: str, payload: ApprovalRequest, _auth=Depends(require_lender), db: Session = Depends(get_db)):
    model = db.get(RegisteredModel, model_id)
    if model is None:
        raise HTTPException(404, "NOT_FOUND")
    if model.status != "APPROVED":
        raise HTTPException(409, "INVALID_MODEL_STATE")
    if config.lender_pubkey and payload.lender_pubkey.lower() != config.lender_pubkey.lower():
        raise HTTPException(400, "INVALID_SIGNATURE")
    if not verify_ed25519(payload.lender_pubkey, payload.lender_sig,
                          lender_approval_payload(model.id, model.commitment, "REVOKE", model.circuit_hash, model.feature_schema_hash)):
        raise HTTPException(400, "INVALID_SIGNATURE")
    from datetime import datetime, timezone
    model.status = "REVOKED"
    model.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
    model.lender_sig = payload.lender_sig
    policies = db.execute(select(Policy).where(Policy.model_commitment == model.commitment,
        Policy.status == "ACTIVE")).scalars().all()
    for policy in policies:
        policy.status = "REVOKED"
    db.commit()
    return {"model_id": model.id, "status": model.status, "revoked_policies": len(policies)}


@router.get("/v1/models")
def list_models(db: Session = Depends(get_db)):
    models = db.execute(select(RegisteredModel).order_by(RegisteredModel.registered_at.desc())).scalars().all()
    return {"items": [model_public(m) for m in models], "total": len(models)}


@router.get("/v1/models/{model_id}")
def get_model(model_id: str, db: Session = Depends(get_db)):
    model = db.get(RegisteredModel, model_id)
    if model is None:
        raise HTTPException(404, "NOT_FOUND")
    return model_public(model)
