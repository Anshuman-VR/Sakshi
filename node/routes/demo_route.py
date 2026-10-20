"""Demo loan application endpoint executing the complete verification pipeline."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from typing import Dict, Optional, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from node.database import get_db
from node.models import Decision, Policy, RegisteredModel, InputBinding, ProofRecord
from node.services.verifier import VerifierEngine, proof_digest
from node.services.ledger import LedgerService
from shared.types import compute_input_hash, compute_application_hash, FEATURE_ORDER
from circuits.prove import generate_zk_proof

router = APIRouter(prefix="/v1/demo", tags=["demo"])

ROOT = Path(__file__).resolve().parents[2]
PERSONAS_PATH = ROOT / "model" / "demo_personas.json"
EXAMPLE_POLICY_PATH = ROOT / "policy" / "example_policy.json"


def _ensure_demo_fixtures(db: Session) -> Policy:
    """Ensure the standard demo model and dual-signed policy exist in database."""
    if not EXAMPLE_POLICY_PATH.is_file():
        raise HTTPException(status_code=500, detail="example_policy.json missing")
    policy_doc = json.loads(EXAMPLE_POLICY_PATH.read_text(encoding="utf-8"))
    
    # 1. Registered Model
    model = db.execute(select(RegisteredModel).where(
        RegisteredModel.commitment == policy_doc["model_commitment"]
    )).scalar_one_or_none()
    
    if model is None:
        model = RegisteredModel(
            id="m_scorecard_v1",
            commitment=policy_doc["model_commitment"],
            circuit_hash=policy_doc["circuit_hash"],
            vk=json.dumps({"format": "sakshi-vk-demo", "circuit_hash": policy_doc["circuit_hash"]}),
            feature_schema_hash=policy_doc["feature_schema_hash"],
            parity_report={"float_auc": 0.794, "quantized_auc": 0.794, "agreement_pct": 100.0},
            lsp_sig=policy_doc["lsp_sig"],
            lsp_pubkey=policy_doc["lsp_pubkey"],
            status="APPROVED",
            lender_sig=policy_doc["lender_sig"],
            registered_at=datetime.now(timezone.utc).replace(tzinfo=None),
            approved_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(model)
        db.flush()

    # 2. Policy
    policy = db.get(Policy, policy_doc["policy_id"])
    if policy is None:
        policy = Policy(
            policy_id=policy_doc["policy_id"],
            version=policy_doc["version"],
            lender_id=policy_doc["lender_id"],
            lsp_id=policy_doc["lsp_id"],
            product=policy_doc["product"],
            model_commitment=policy_doc["model_commitment"],
            circuit_hash=policy_doc["circuit_hash"],
            feature_schema_hash=policy_doc["feature_schema_hash"],
            decision_threshold=float(policy_doc["decision_threshold"]),
            fixed_point_scale=int(policy_doc["fixed_point_scale"]),
            hard_rules=policy_doc.get("hard_rules", []),
            proof_sla_minutes=int(policy_doc.get("proof_sla_minutes", 10)),
            valid_from=datetime.fromisoformat(policy_doc["valid_from"].replace("Z", "+00:00")).replace(tzinfo=None),
            valid_to=datetime.fromisoformat(policy_doc["valid_to"].replace("Z", "+00:00")).replace(tzinfo=None),
            lsp_sig=policy_doc["lsp_sig"],
            lender_sig=policy_doc["lender_sig"],
            lsp_pubkey=policy_doc["lsp_pubkey"],
            lender_pubkey=policy_doc["lender_pubkey"],
            policy_hash=policy_doc["policy_hash"],
            canonical_document=policy_doc,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            status="ACTIVE",
        )
        db.add(policy)
        db.flush()
    
    return policy


class DemoApplyRequest(BaseModel):
    application_id: Optional[str] = None
    policy_id: Optional[str] = None
    persona: Optional[str] = Field(None, description="persona ID or name substring: 'priya', 'rahul', 'amit'")
    features: Optional[Dict[str, float]] = None
    tamper: Optional[str] = Field(None, description="Optional tamper mode: 'model', 'threshold', 'input'")


@router.post("/apply")
def demo_apply(request: DemoApplyRequest, db: Session = Depends(get_db)):
    """Live demo application endpoint.
    
    Executes the REAL end-to-end conformance pipeline:
    1. Evaluates loan features.
    2. Issues notice to lender node.
    3. Records input commitment binding.
    4. Proves decision conformance (honest or simulated tamper).
    5. Verifier checks V1-V9.
    6. Writes entry to the immutable hash-chained audit ledger.
    """
    policy = _ensure_demo_fixtures(db)
    
    # Resolve features from persona or explicit features
    features: Dict[str, float] = {}
    if request.features:
        features = {k: float(v) for k, v in request.features.items() if k in FEATURE_ORDER}
    elif PERSONAS_PATH.is_file():
        personas_data = json.loads(PERSONAS_PATH.read_text(encoding="utf-8")).get("personas", [])
        chosen = personas_data[0] # Default: Priya (Prime)
        if request.persona:
            key = request.persona.lower()
            for p in personas_data:
                if key in p["id"].lower() or key in p["name"].lower():
                    chosen = p
                    break
        features = chosen["features"]
    
    if not features:
        features = {
            "bureau_score": 750.0,
            "monthly_income": 80000.0,
            "foir": 0.30,
            "loan_tenure_months": 36.0,
            "num_active_loans": 1.0,
            "num_enquiries_6m": 0.0,
            "bank_account_age_months": 60.0,
            "loan_amount_requested": 150000.0,
            "behaviour_idx": 0.20,
            "employment_type": 0.0,
        }
    
    # Assess underwriting rules
    bureau = features.get("bureau_score", 0.0)
    foir = features.get("foir", 1.0)
    honest_decision = 1 if (bureau >= 600.0 and foir <= 0.65) else 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    decision_id = f"d_demo_{uuid.uuid4().hex[:8]}"
    app_id = request.application_id or f"app_demo_{uuid.uuid4().hex[:8]}"
    app_hash = compute_application_hash(app_id)
    x_prime = compute_input_hash(features)

    # 1. Register Decision Notice (Starts SLA)
    decision_record = Decision(
        decision_id=decision_id,
        application_id_hash=app_hash,
        policy_id=policy.policy_id,
        decision=honest_decision,
        ts=now,
        status="NOTICE_RECEIVED",
        sla_deadline=now + timedelta(minutes=policy.proof_sla_minutes),
        received_at=now,
    )
    db.add(decision_record)
    
    # 2. Register Input Binding (Lender Side)
    if request.tamper == "input":
        # Simulate tampering on the lender-side adapter comparison
        binding_x = "0x" + "bad" * 21 + "0"
    else:
        binding_x = x_prime

    binding = InputBinding(
        id=f"bind_{uuid.uuid4().hex[:12]}",
        application_id_hash=app_hash,
        x_prime=binding_x,
        decision_id=decision_id,
        bound_at=now,
        binding_status="PENDING",
    )
    db.add(binding)
    db.flush()

    # 3. Generate ZK / Attestation Proof
    proof_threshold = 0.05 if request.tamper == "threshold" else policy.decision_threshold
    proof_commitment = "0x" + "dead" * 16 if request.tamper == "model" else policy.model_commitment

    proof_payload = generate_zk_proof(
        decision_id=decision_id,
        policy_id=policy.policy_id,
        features=features,
        decision=honest_decision,
        policy_hash=policy.policy_hash,
        model_commitment=proof_commitment,
        threshold=proof_threshold,
        allow_mock=True,
    )

    # 4. Run Verifier Engine
    verification_id = f"v_demo_{uuid.uuid4().hex[:8]}"
    proof_bytes, proof_hash, _ = proof_digest(proof_payload)
    
    # Reserve proof record
    proof_rec = ProofRecord(
        id=verification_id,
        decision_id=decision_id,
        proof_hash=proof_hash,
        proof_blob=proof_bytes,
        public_inputs=proof_payload.public_inputs.model_dump(mode="json"),
        status="PENDING",
        submitted_at=now,
    )
    db.add(proof_rec)
    db.flush()

    result = VerifierEngine.run_pipeline(db, proof_payload, verification_id=verification_id)

    # 5. Commit Decision & Ledger
    proof_rec.status = result.status
    proof_rec.reason = result.reason
    decision_record.status = result.status
    decision_record.failure_reason = result.reason

    if result.status == "VERIFIED":
        decision_record.verified_at = now
        decision_record.verification_id = verification_id
        decision_record.model_commitment = proof_payload.public_inputs.C
        ledger_entry = LedgerService.append(
            db,
            decision_id=decision_id,
            verification_id=verification_id,
            status="VERIFIED",
            reason=None,
            policy_id=policy.policy_id,
            model_commitment=proof_payload.public_inputs.C,
            proof_hash=proof_hash,
        )
        decision_record.ledger_seq = ledger_entry.seq
    else:
        ledger_entry = LedgerService.append(
            db,
            decision_id=decision_id,
            verification_id=verification_id,
            status="FAILED",
            reason=result.reason,
            policy_id=policy.policy_id,
            model_commitment=proof_payload.public_inputs.C,
            proof_hash=proof_hash,
        )
        decision_record.ledger_seq = ledger_entry.seq

    db.commit()

    return {
        "decision_id": decision_id,
        "application_id": app_id,
        "status": result.status,
        "decision": honest_decision,
        "decision_label": "APPROVED" if honest_decision == 1 else "REJECTED",
        "policy_id": policy.policy_id,
        "model_commitment": policy.model_commitment,
        "ledger_seq": decision_record.ledger_seq,
        "verified_at": decision_record.verified_at.isoformat() if decision_record.verified_at else None,
        "failure_reason": result.reason,
        "failed_at_step": result.failed_at_step,
    }
