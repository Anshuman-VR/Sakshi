"""Lender-side input commitment reconciliation endpoint."""
import re, uuid
from pydantic import BaseModel, ConfigDict, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from node.database import get_db
from node.models import Decision, InputBinding, ProofRecord
from node.routes.deps import require_lender

router = APIRouter(tags=["input bindings"])


class BindingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_id_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")
    x_prime: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")
    decision_id: str | None = None


@router.post("/v1/input-bindings")
def create_binding(payload: BindingRequest, _auth=Depends(require_lender), db: Session = Depends(get_db)):
    # Raw features never cross into the Lender Node; the lender-side adapter
    # computes X' locally and sends only the commitment.
    query = select(Decision).where(Decision.application_id_hash == payload.application_id_hash.lower())
    if payload.decision_id:
        query = query.where(Decision.decision_id == payload.decision_id)
    decisions = db.execute(query).scalars().all()
    if not decisions:
        raise HTTPException(404, "DECISION_NOT_FOUND")
    if len(decisions) != 1:
        raise HTTPException(409, "AMBIGUOUS_APPLICATION")
    decision = decisions[0]
    existing = db.execute(select(InputBinding).where(InputBinding.decision_id == decision.decision_id)).scalar_one_or_none()
    if existing is not None:
        if existing.application_id_hash != payload.application_id_hash.lower() or existing.x_prime != payload.x_prime.lower():
            raise HTTPException(409, "BINDING_ALREADY_SET")
        return {"bound": existing.binding_status == "MATCHED", "binding_status": existing.binding_status,
                "decision_id": decision.decision_id, "binding_id": existing.id}
    proof = db.execute(select(ProofRecord).where(ProofRecord.decision_id == decision.decision_id)
        .order_by(ProofRecord.submitted_at.desc())).scalars().first()
    if proof is None:
        binding_status = "PENDING"
    else:
        expected_x = proof.public_inputs.get("X")
        binding_status = "MATCHED" if isinstance(expected_x, str) and payload.x_prime.lower() == expected_x.lower() else "MISMATCH"
    binding = InputBinding(id=f"b_{uuid.uuid4().hex}", application_id_hash=payload.application_id_hash.lower(),
        x_prime=payload.x_prime.lower(), decision_id=decision.decision_id, binding_status=binding_status)
    db.add(binding)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "BINDING_ALREADY_SET")
    return {"bound": binding_status == "MATCHED", "binding_status": binding_status,
            "decision_id": decision.decision_id, "binding_id": binding.id}
