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
    "decision_threshold": 0.5,
    "feature_schema_hash": "71dbb8d4f57eec37feb01e1434ccdd9efc4b45bd92119eb88a31caf3243779d3",
    "fixed_point_scale": 1024,
    "hard_rules": [
        {"feature": "bureau_score", "id": "R1", "op": "gte", "value": 600.0},
        {"feature": "foir", "id": "R2", "op": "lte", "value": 0.65}
    ],
    "lender_id": "meridian_digital",
    "lender_pubkey": "8ea9dcf81ea9df5ca7151de034820a9b5b939014b3900b2b6c6c35cee7b619c7",
    "lender_sig": "9f0292824c0b4951e049ce24f553776bd027255b792b91ba26c410252994eb73f708a8e94d53879791439fbab22401497005bcbfb50f7fd17ffcfbb4b46ca503",
    "lsp_id": "quick_fincorp",
    "lsp_pubkey": "62956a00307eccd79445148711f0693803352106ac9d64b3cf650e913476e5f3",
    "lsp_sig": "9228c3896b94b9757f1f8111b3b22c147625ad613b0f643c1a993c57282c605d2d7eb8899c504f099fa5f3e27c51201e43d12178f725436d1b0b2fce43cbe904",
    "model_commitment": "0xd031786a1e637500b6c16c661f33e751cc13e0c614eeb03045866660aeb09b80",
    "policy_hash": "f2f6778a81599ce4a9fbeebe1f0c337f37bfde894297632f1cee3581fcd32b9f",
    "policy_id": "pol_meridian_quickfin_v1",
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
        "loan_tenure_months": 24.0,
        "num_active_loans": 2.0,
        "num_enquiries_6m": 1.0,
        "bank_account_age_months": 45.0,
        "loan_amount_requested": 80000.0,
        "behaviour_idx": 0.45,
        "employment_type": 0.0
    }
}

DEFAULT_CUSTOMER_INFO = {
    "priya": {
        "name": "Priya Sharma",
        "phone": "+91 98201 44821",
        "pan": "BNZPS1042K",
        "bank_account": "9182014482103",
        "ifsc": "HDFC0001234",
        "employment": "Senior Software Engineer",
        "monthly_income": 95000,
        "loan_amount": 150000,
        "tenure": 36,
        "bureau": 758,
    },
    "rahul": {
        "name": "Rahul Verma",
        "phone": "+91 97112 55290",
        "pan": "AXRPV8841M",
        "bank_account": "8871125529041",
        "ifsc": "ICIC0000456",
        "employment": "Logistics Executive (Gig / Contract)",
        "monthly_income": 32000,
        "loan_amount": 200000,
        "tenure": 36,
        "bureau": 542,
    },
    "amit": {
        "name": "Amit Patel",
        "phone": "+91 99042 18834",
        "pan": "CPZPA3391J",
        "bank_account": "5504218834092",
        "ifsc": "SBIN0002100",
        "employment": "Retail Store Owner (Self-Employed)",
        "monthly_income": 52000,
        "loan_amount": 80000,
        "tenure": 24,
        "bureau": 672,
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
    customer_info: Optional[Dict[str, Any]] = None
    tamper: Optional[str] = Field(None, description="'model', 'threshold', 'input', 'replay', 'invalid_zk', 'policy'")


@router.post("/apply")
def demo_apply(request: DemoApplyRequest, db: Session = Depends(get_db)):
    """Executes the end-to-end conformance pipeline with optional tamper simulation."""
    policy = _ensure_demo_fixtures(db)
    
    # Resolve persona key
    persona_key = "priya"
    if request.persona:
        key = request.persona.lower()
        for p_name in DEFAULT_PERSONAS.keys():
            if key in p_name:
                persona_key = p_name
                break

    # Resolve features
    features: Dict[str, float] = {}
    if request.features:
        features = {k: float(v) for k, v in request.features.items() if k in FEATURE_ORDER}
    else:
        features = DEFAULT_PERSONAS.get(persona_key, DEFAULT_PERSONAS["priya"])
    
    # Resolve customer info
    customer_data = dict(DEFAULT_CUSTOMER_INFO.get(persona_key, DEFAULT_CUSTOMER_INFO["priya"]))
    if request.customer_info:
        customer_data.update(request.customer_info)

    # Assess underwriting rules at policy threshold (0.50)
    bureau = features.get("bureau_score", 0.0)
    foir = features.get("foir", 1.0)
    honest_decision = 1 if (bureau >= 600.0 and foir <= 0.65 and persona_key != "rahul") else 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    unique_suffix = uuid.uuid4().hex[:8].upper()
    decision_id = f"QL_{unique_suffix}"
    app_id = request.application_id or f"app_QL_{unique_suffix}"
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
        customer_info=customer_data,
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
    verification_id = f"v_QL_{unique_suffix}"
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
            "description": f"Verifies policy {policy.policy_id} is active and dual-signed",
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
        "customer_info": customer_data,
        "proof": proof_b64,
        "proof_hash": proof_hash,
        "proof_size_bytes": len(proof_bytes_dec),
        "public_inputs": proof_payload.public_inputs.model_dump(mode="json"),
        "steps_evaluated": steps_evaluated,
    }
