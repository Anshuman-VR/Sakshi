"""Demo loan application endpoint executing the complete verification pipeline."""
from datetime import datetime, timezone, timedelta
import base64
import json
from pathlib import Path
from typing import Dict, Optional, Any, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from node.database import get_db
from node.models import Decision, Policy, RegisteredModel, InputBinding, ProofRecord
from node.services.verifier import VerifierEngine, proof_digest
from node.services.ledger import LedgerService
from shared.types import compute_input_hash, compute_application_hash, FEATURE_ORDER, today_epoch, ProofPayload, PublicInputs

router = APIRouter(prefix="/v1/demo", tags=["demo"])

DEFAULT_DEMO_POLICY = {
    "circuit_hash": "0xd3b2dc63f9c9520b6d22069a015b36288d90676f45cf9bd5a41ec133911b6729",
    "decision_threshold": 0.2,
    "feature_schema_hash": "71dbb8d4f57eec37feb01e1434ccdd9efc4b45bd92119eb88a31caf3243779d3",
    "fixed_point_scale": 1024,
    "hard_rules": [
        {"feature": "bureau_score", "id": "R1", "op": "gte", "value": 600.0},
        {"feature": "foir", "id": "R2", "op": "lte", "value": 0.65}
    ],
    "lender_id": "nbfc42_capital",
    "lender_pubkey": "ed8976c0add040cad9deaf28460a02b3da80d1fa0c9caf80377814715680910d",
    "lender_sig": "1c829621bedd289a699022d2dba1bec6d02b575135e850237345c58ffd4f4fd41d146686411b5445f9875d11be17bb384b55e3948882c696e472c6ffaf71950a",
    "lsp_id": "lspX_fintech",
    "lsp_pubkey": "bbce578fdc8db2fdc27764eed4ce988bf671b5d546dce0c3101b8d9ed83ed94e",
    "lsp_sig": "aaacd1a2cbdd6ced1fab7b285911495ab29cd0786d50be8a02b94e7aecbed39d5f78b3d687afe0a1b305879c97d32a975ba5c44c60c1a16520a195da4dd99a0f",
    "model_commitment": "0xd031786a1e637500b6c16c661f33e751cc13e0c614eeb03045866660aeb09b80",
    "policy_hash": "447930887ea48c1d40442e0a7c3ba681d9168e663df2d9920ddb814cfb5cbf47",
    "policy_id": "pol_nbfc42_lspX_personal_v1",
    "product": "personal_loan",
    "proof_sla_minutes": 10,
    "valid_from": "2026-10-20T00:00:00Z",
    "valid_to": "2027-10-20T00:00:00Z",
    "version": 1
}

DEFAULT_PERSONAS = {
    "priya": {
        "bureau_score": 758.0,
        "monthly_income": 95000.0,
        "foir": 0.28,
        "loan_tenure_months": 36.0,
        "num_active_loans": 1.0,
        "num_enquiries_6m": 0.0,
        "bank_account_age_months": 84.0,
        "loan_amount_requested": 150000.0,
        "behaviour_idx": 0.18,
        "employment_type": 0.0
    },
    "rahul": {
        "bureau_score": 542.0,
        "monthly_income": 32000.0,
        "foir": 0.68,
        "loan_tenure_months": 36.0,
        "num_active_loans": 5.0,
        "num_enquiries_6m": 4.0,
        "bank_account_age_months": 22.0,
        "loan_amount_requested": 200000.0,
        "behaviour_idx": 0.88,
        "employment_type": 1.0
    },
    "amit": {
        "bureau_score": 672.0,
        "monthly_income": 52000.0,
        "foir": 0.44,
        "loan_tenure_months": 36.0,
        "num_active_loans": 2.0,
        "num_enquiries_6m": 1.0,
        "bank_account_age_months": 45.0,
        "loan_amount_requested": 80000.0,
        "behaviour_idx": 0.45,
        "employment_type": 0.0
    }
}


def _ensure_demo_fixtures(db: Session) -> Policy:
    """Ensure the standard demo model and dual-signed policy exist in database."""
    policy_doc = DEFAULT_DEMO_POLICY
    
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
    persona: Optional[str] = Field(None, description="persona ID: 'priya', 'rahul', 'amit'")
    features: Optional[Dict[str, float]] = None
    tamper: Optional[str] = Field(None, description="'model', 'threshold', 'input', 'replay', 'invalid_zk', 'policy'")


@router.post("/apply")
def demo_apply(request: DemoApplyRequest, db: Session = Depends(get_db)):
    """Executes the end-to-end conformance pipeline with optional tamper simulation."""
    policy = _ensure_demo_fixtures(db)
    
    # Resolve features
    features: Dict[str, float] = {}
    if request.features:
        features = {k: float(v) for k, v in request.features.items() if k in FEATURE_ORDER}
    elif request.persona:
        key = request.persona.lower()
        for p_name, p_features in DEFAULT_PERSONAS.items():
            if key in p_name:
                features = p_features
                break
    
    if not features:
        features = DEFAULT_PERSONAS["priya"]
    
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

    # 3. Generate Proof Payload
    proof_threshold = 0.05 if request.tamper == "threshold" else policy.decision_threshold
    proof_commitment = "0x" + "dead" * 16 if request.tamper == "model" else policy.model_commitment
    proof_policy_hash = "0x" + "badc0de" * 8 if request.tamper == "policy" else policy.policy_hash

    if request.tamper == "replay":
        # Find a previous proof to replay
        prev_proof = db.execute(select(ProofRecord).order_by(ProofRecord.submitted_at.desc()).limit(1)).scalar_one_or_none()
        if prev_proof is not None:
            proof_bytes = prev_proof.proof_blob
        else:
            proof_bytes = b"SAKSHI_TEST_VALID_PROOF:seed_for_replay"
    elif request.tamper == "invalid_zk":
        proof_bytes = b"CORRUPTED_MALFORMED_CIRCUIT_PROOF_BYTES_0xDEAD"
    else:
        proof_bytes = f"SAKSHI_TEST_VALID_PROOF:{decision_id}".encode("utf-8")

    proof_b64 = base64.b64encode(proof_bytes).decode("ascii")

    proof_payload = ProofPayload(
        decision_id=decision_id,
        policy_id=policy.policy_id,
        proof=proof_b64,
        public_inputs=PublicInputs(
            policy_hash=proof_policy_hash,
            C=proof_commitment,
            X=x_prime,
            decision=honest_decision,
            threshold=float(proof_threshold),
            epoch=today_epoch(),
        )
    )

    # 4. Run Verifier Engine
    verification_id = f"v_demo_{uuid.uuid4().hex[:8]}"
    proof_bytes_dec, proof_hash, _ = proof_digest(proof_payload)
    
    # Check if proof already exists (replay check before reservation)
    existing_by_hash = db.execute(select(ProofRecord.id).where(ProofRecord.proof_hash == proof_hash)).scalar_one_or_none()
    proof_rec = None
    if existing_by_hash is None:
        proof_rec = ProofRecord(
            id=verification_id,
            decision_id=decision_id,
            proof_hash=proof_hash,
            proof_blob=proof_bytes_dec,
            public_inputs=proof_payload.public_inputs.model_dump(mode="json"),
            status="PENDING",
            submitted_at=now,
        )
        db.add(proof_rec)
        db.flush()

    result = VerifierEngine.run_pipeline(db, proof_payload, verification_id=verification_id)

    # 5. Commit Decision & Ledger
    if proof_rec is not None:
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

    steps_evaluated = [
        {
            "step": "V1_POLICY_EXISTS",
            "name": "Mutual Policy Registry",
            "description": "Verifies contractual policy is active and dual-signed",
            "passed": result.failed_at_step != "V1_POLICY_EXISTS",
        },
        {
            "step": "V2_MODEL_APPROVED",
            "name": "Model Commitment Match (C)",
            "description": f"Compares C against registered model ({policy.model_commitment[:16]}...)",
            "passed": result.failed_at_step != "V2_MODEL_APPROVED",
            "expected": policy.model_commitment,
            "actual": proof_payload.public_inputs.C,
        },
        {
            "step": "V3_POLICY_HASH_MATCH",
            "name": "Canonical Policy Digest",
            "description": "Compares contract terms hash against agreed policy document",
            "passed": result.failed_at_step != "V3_POLICY_HASH_MATCH",
            "expected": policy.policy_hash,
            "actual": proof_payload.public_inputs.policy_hash,
        },
        {
            "step": "V4_THRESHOLD_MATCH",
            "name": "Decision Cutoff Consistency",
            "description": f"Verifies claimed threshold against policy ({policy.decision_threshold:.3f})",
            "passed": result.failed_at_step != "V4_THRESHOLD_MATCH",
            "expected": float(policy.decision_threshold),
            "actual": float(proof_payload.public_inputs.threshold),
        },
        {
            "step": "V5_WINDOW_VALID",
            "name": "Proving Epoch Window",
            "description": f"Ensures proving timestamp epoch ({today_epoch()}) is valid",
            "passed": result.failed_at_step != "V5_WINDOW_VALID",
        },
        {
            "step": "V6_UNIQUENESS",
            "name": "Proof Uniqueness (Replay Guard)",
            "description": "Checks that the proof hash has never been consumed before",
            "passed": result.failed_at_step != "V6_UNIQUENESS",
        },
        {
            "step": "V7_DECISION_MATCH",
            "name": "Notice & Input Binding Alignment",
            "description": "Compares lender feature commitment X' with prover witness commitment X",
            "passed": result.failed_at_step != "V7_DECISION_MATCH",
            "binding_status": binding.binding_status,
        },
        {
            "step": "V8_ZK_VERIFY",
            "name": "Halo2 Zero-Knowledge Proof Verification",
            "description": "Cryptographically validates polynomial constraints of the credit scorecard circuit",
            "passed": result.failed_at_step != "V8_ZK_VERIFY",
        },
        {
            "step": "V9_HARD_RULES",
            "name": "Underwriting Hard Rules",
            "description": "Enforces mandatory boundaries (CIBIL >= 600, FOIR <= 65%)",
            "passed": result.failed_at_step != "V9_HARD_RULES",
        },
    ]

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
        "proof": proof_b64,
        "proof_hash": proof_hash,
        "proof_size_bytes": len(proof_bytes_dec),
        "public_inputs": proof_payload.public_inputs.model_dump(mode="json"),
        "steps_evaluated": steps_evaluated,
    }
