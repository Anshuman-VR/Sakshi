"""
Sakshi - Shared Contract Types
READ-ONLY after Hour 2 of hackathon.
All three branches import from this module.
Do NOT modify without coordinating with all developers.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime
import hashlib
import json

# ============================================================
# CONSTANTS & CANONICAL SCHEMA
# ============================================================

# Feature order MUST be consistent between sidecar (witness builder) 
# and any downstream component that recomputes X or checks binding.
# Dev 1 defines this list. Never reorder without retraining + recompiling circuit.
FEATURE_ORDER: List[str] = [
    'bureau_score',
    'monthly_income',
    'foir',
    'loan_tenure_months',
    'num_active_loans',
    'num_enquiries_6m',
    'bank_account_age_months',
    'loan_amount_requested',
    'behaviour_idx',
    'employment_type',
]

# Fixed-point scale: all floats multiplied by this before ZK circuit
FIXED_POINT_SCALE: int = 1024

# ============================================================
# DECISION LIFECYCLE TYPES
# ============================================================

DecisionStatusLiteral = Literal[
    'NOT_FOUND',
    'NOTICE_RECEIVED',  # Decision notice posted, awaiting proof
    'VERIFIED',         # Proof verified successfully
    'FAILED',           # Proof verification failed
    'EXPIRED',          # SLA exceeded before proof arrived
]

FailureReason = Literal[
    'MODEL_MISMATCH',        # V2: commitment C not in approved models
    'POLICY_NOT_FOUND',      # V1: policy_id unknown
    'POLICY_EXPIRED',        # V1: policy validity window passed
    'POLICY_HASH_MISMATCH',  # V3: policy_hash does not match stored hash
    'THRESHOLD_MISMATCH',    # V4: claimed threshold != policy threshold
    'WINDOW_INVALID',        # V5: epoch outside valid window
    'REPLAY',                # V6: proof_hash already seen
    'DECISION_MISMATCH',     # V7: proof decision != notice decision
    'INVALID_PROOF',         # V8: EZKL verification failed
    'HARD_RULE_VIOLATION',   # V9: hard rule in policy violated
    'EXPIRED',               # SLA timer
    'BINDING_MISMATCH',      # Input binding adapter: X' != X
]

JobStatusLiteral = Literal['QUEUED', 'PROVING', 'UPLOADED', 'VERIFIED', 'FAILED']

ModelStatusLiteral = Literal['PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'REVOKED']

# ============================================================
# SHARED PYDANTIC MODELS
# ============================================================

class DecisionEvent(BaseModel):
    """
    Input to the sidecar. Represents a credit decision made by the LSP model.
    This stays INSIDE the LSP zone. Never sent to the Lender Node directly.
    """
    decision_id: str = Field(..., example='d_8842')
    application_id: str = Field(..., example='a_5531')
    policy_id: str = Field(..., example='pol_demo_v1')
    features: Dict[str, float] = Field(..., description='Raw features - stays in LSP zone')
    decision: int = Field(..., ge=0, le=1, description='1=approve, 0=reject')
    ts: str = Field(..., description='ISO 8601 timestamp of decision')


class DecisionNotice(BaseModel):
    """
    Posted from sidecar to Lender Node. Starts the SLA clock.
    Contains NO raw features, NO model weights.
    """
    decision_id: str
    application_id_hash: str = Field(..., description='SHA-256 hex of application_id')
    policy_id: str
    decision: int = Field(..., ge=0, le=1)
    ts: str


class PublicInputs(BaseModel):
    """
    Public inputs included with a ZK proof.
    These are the values the verifier checks against policy.
    """
    policy_hash: str = Field(..., description='SHA-256 of canonical policy JSON')
    C: str = Field(..., description='Model commitment (SHA-256 of salted model params)')
    X: str = Field(..., description='Input commitment (SHA-256 of canonical features)')
    decision: int = Field(..., ge=0, le=1)
    threshold: float = Field(..., description='Decision threshold (e.g. 0.200)')
    epoch: int = Field(..., description='Date as integer YYYYMMDD for replay window')


class ProofPayload(BaseModel):
    """
    Posted from sidecar to Lender Node /v1/proofs.
    """
    decision_id: str
    policy_id: str
    proof: str = Field(..., description='Base64-encoded EZKL proof bytes')
    public_inputs: PublicInputs


class ModelRegistration(BaseModel):
    """
    Posted from LSP to Lender Node /v1/models.
    Contains ONLY public data - no weights, no proving key.
    """
    commitment: str = Field(..., description='SHA-256 hex of salted model params = C')
    circuit_hash: str = Field(..., description='SHA-256 of compiled EZKL circuit')
    vk: str = Field(..., description='Base64-encoded EZKL verification key')
    feature_schema_hash: str = Field(..., description='SHA-256 of feature schema JSON')
    parity_report: Dict[str, Any] = Field(
        ...,
        description='Float vs quantized accuracy comparison: {float_auc, quantized_auc, agreement_pct, test_samples}'
    )
    lsp_sig: str = Field(..., description='Ed25519 signature over canonical registration JSON (hex)')
    lsp_pubkey: str = Field(..., description='Ed25519 public key (hex)')


class HardRule(BaseModel):
    id: str
    feature: str
    op: Literal['gte', 'lte', 'eq', 'neq']
    value: float


class PolicyDocument(BaseModel):
    """
    Dual-signed policy document. Both lender and LSP must sign.
    This is the contract made machine-verifiable.
    """
    policy_id: str
    version: int
    lender_id: str
    lsp_id: str
    product: str
    model_commitment: str = Field(..., description='C - must match an APPROVED model')
    circuit_hash: str
    feature_schema_hash: str
    decision_threshold: float = Field(..., description='e.g. 0.200')
    fixed_point_scale: int = Field(default=1024)
    hard_rules: List[HardRule] = Field(default_factory=list)
    proof_sla_minutes: int = Field(default=10)
    valid_from: str = Field(..., description='ISO 8601')
    valid_to: str = Field(..., description='ISO 8601')
    lsp_sig: str = Field(..., description='Ed25519 sig (hex)')
    lender_sig: str = Field(..., description='Ed25519 sig (hex)')
    lsp_pubkey: str
    lender_pubkey: str
    
    def canonical_json(self) -> str:
        """Canonical JSON for signing. Excludes signatures."""
        d = self.model_dump(exclude={'lsp_sig', 'lender_sig'})
        return json.dumps(d, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    
    def policy_hash(self) -> str:
        """SHA-256 of canonical JSON. Used in proof public inputs."""
        return hashlib.sha256(self.canonical_json().encode('utf-8')).hexdigest()


class VerificationResult(BaseModel):
    """
    Result of running the verification pipeline.
    Written to the audit ledger.
    """
    verification_id: str
    decision_id: str
    status: Literal['VERIFIED', 'FAILED', 'PENDING']
    reason: Optional[str] = None
    failed_at_step: Optional[str] = None  # e.g. 'V2_MODEL_APPROVED'
    verified_at: Optional[str] = None
    ledger_seq: Optional[int] = None


class LedgerEntry(BaseModel):
    """
    Single row in the append-only audit ledger.
    row_hash = SHA-256(prev_hash + canonical_json(row without row_hash))
    """
    seq: int
    decision_id: str
    verification_id: str
    status: str
    reason: Optional[str] = None
    policy_id: str
    model_commitment: str
    proof_hash: str
    ts: str
    prev_hash: str
    row_hash: str


class JobStatus(BaseModel):
    """
    Status of a proving job in the sidecar.
    """
    job_id: str
    decision_id: str
    status: JobStatusLiteral
    error: Optional[str] = None
    created_at: str
    updated_at: str
    proof_size_bytes: Optional[int] = None
    proving_duration_ms: Optional[int] = None


class DecisionStatusResponse(BaseModel):
    """
    Response from GET /v1/decisions/{id}/status (the gate API).
    This is what the Mock LMS reads to decide whether to disburse.
    """
    decision_id: str
    status: DecisionStatusLiteral
    model_commitment: Optional[str] = None
    policy_id: Optional[str] = None
    verified_at: Optional[str] = None
    ledger_seq: Optional[int] = None
    failure_reason: Optional[str] = None
    sla_deadline: Optional[str] = None


class DashboardSummary(BaseModel):
    """
    Aggregated stats for the lender dashboard.
    Served by GET /v1/dashboard/summary
    """
    total_decisions: int
    verified: int
    failed: int
    pending: int
    expired: int
    failure_breakdown: Dict[str, int] = Field(default_factory=dict)
    recent_decisions: List[DecisionStatusResponse] = Field(default_factory=list)
    proof_latency_p50_ms: Optional[float] = None
    proof_latency_p95_ms: Optional[float] = None
    ledger_seq: int = 0
    chain_valid: bool = True
    active_models: List[Dict[str, Any]] = Field(default_factory=list)
    active_policies: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def compute_sha256(data: bytes) -> str:
    """Returns SHA-256 hex digest."""
    return hashlib.sha256(data).hexdigest()


def compute_input_hash(features: Dict[str, float]) -> str:
    """Canonical SHA-256 hash of feature dict. Must be identical across sidecar and adapter."""
    canonical = json.dumps(
        {k: features[k] for k in FEATURE_ORDER if k in features},
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def compute_application_hash(application_id: str) -> str:
    """SHA-256 of application_id string."""
    return hashlib.sha256(application_id.encode('utf-8')).hexdigest()


def today_epoch() -> int:
    """Today's date as YYYYMMDD integer for replay window."""
    return int(datetime.utcnow().strftime('%Y%m%d'))
