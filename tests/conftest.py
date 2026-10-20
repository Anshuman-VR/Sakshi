"""Isolated lender-node fixtures; no repository database or files are reset."""
import os
os.environ.setdefault("SAKSHI_NODE_ENVIRONMENT", "test")
import base64, hashlib
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from node.config import config
from node.database import get_db
from node.models import Base
from node.main import app
from node.services.crypto import (canonical_json, lender_approval_payload,
    model_registration_signing_payload, policy_signing_payload)
import node.routes.proofs_route as proofs_route
import node.services.sla_monitor as sla_monitor


def _keypair():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    return private, public


@pytest.fixture
def environment(monkeypatch):
    lender_private, lender_public = _keypair()
    lsp_private, lsp_public = _keypair()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(proofs_route, "SessionLocal", TestSession)
    monkeypatch.setattr(sla_monitor, "SessionLocal", TestSession)
    config.sidecar_api_key = SecretStr("test-sidecar-secret")
    config.lender_admin_key = SecretStr("test-lender-secret")
    config.lsp_pubkey = lsp_public
    config.lender_pubkey = lender_public
    config.environment = "test"
    config.mock_verify = True
    config.ezkl_settings_path = ""
    config.proof_max_bytes = 5_000_000
    config.sla_poll_seconds = 60
    with TestClient(app) as client:
        yield {"client": client, "session": TestSession, "engine": engine,
               "lender_private": lender_private, "lender_public": lender_public,
               "lsp_private": lsp_private, "lsp_public": lsp_public}
    app.dependency_overrides.clear()
    engine.dispose()


def register_model(env):
    c = env["client"]
    commitment = "c" * 64
    model_data = {"commitment": commitment, "circuit_hash": "a" * 64,
        "vk": base64.b64encode(b'{"vk":"test"}').decode(),
        "feature_schema_hash": "b" * 64,
        "parity_report": {"float_auc": 0.8, "quantized_auc": 0.79, "agreement_pct": 99.2, "test_samples": 100},
        "lsp_pubkey": env["lsp_public"], "lsp_sig": ""}
    model_data["lsp_sig"] = env["lsp_private"].sign(model_registration_signing_payload(model_data)).hex()
    r = c.post("/v1/models", json=model_data, headers={"X-Sakshi-Key": "test-sidecar-secret"})
    assert r.status_code == 201, r.text
    model_id = r.json()["model_id"]
    signature = env["lender_private"].sign(lender_approval_payload(model_id, commitment, circuit_hash="a" * 64, feature_schema_hash="b" * 64)).hex()
    r = c.post(f"/v1/models/{model_id}/approve", json={"lender_sig": signature,
        "lender_pubkey": env["lender_public"]}, headers={"X-Lender-Key": "test-lender-secret"})
    assert r.status_code == 200, r.text
    return {"model_id": model_id, "commitment": commitment, "circuit_hash": "a" * 64,
            "feature_schema_hash": "b" * 64}


def register_policy(env, model, policy_id="pol_test_v1", hard_rules=None):
    now = datetime.now(timezone.utc)
    policy_data = {"policy_id": policy_id, "version": 1, "lender_id": "lender-test", "lsp_id": "lsp-test",
        "product": "personal_loan", "model_commitment": model["commitment"],
        "circuit_hash": model["circuit_hash"], "feature_schema_hash": model["feature_schema_hash"],
        "decision_threshold": 0.2, "fixed_point_scale": 1024,
        "hard_rules": hard_rules or [], "proof_sla_minutes": 10,
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_to": (now + timedelta(days=1)).isoformat(),
        "lsp_sig": "", "lender_sig": "", "lsp_pubkey": env["lsp_public"],
        "lender_pubkey": env["lender_public"]}
    from shared.types import PolicyDocument
    normalized = PolicyDocument.model_validate(policy_data).model_dump(mode="json")
    signing_bytes = policy_signing_payload(normalized)
    policy_data["lsp_sig"] = env["lsp_private"].sign(signing_bytes).hex()
    policy_data["lender_sig"] = env["lender_private"].sign(signing_bytes).hex()
    r = env["client"].post("/v1/policies", json=policy_data, headers={"X-Sakshi-Key": "test-sidecar-secret"})
    assert r.status_code == 201, r.text
    from shared.types import PolicyDocument
    policy_hash = PolicyDocument.model_validate(policy_data).policy_hash()
    return {"policy_id": policy_id, "policy_hash": policy_hash, "model": model, "data": policy_data}


def create_notice(env, policy, decision_id="d_test_1", decision=1, app_id="application-1"):
    now = datetime.now(timezone.utc)
    app_hash = hashlib.sha256(app_id.encode()).hexdigest()
    data = {"decision_id": decision_id, "application_id_hash": app_hash,
            "policy_id": policy["policy_id"], "decision": decision, "ts": now.isoformat()}
    r = env["client"].post("/v1/decisions", json=data, headers={"X-Sakshi-Key": "test-sidecar-secret"})
    assert r.status_code == 202, r.text
    features = {"bureau_score": 720.0, "monthly_income": 50000.0, "foir": 0.3,
        "loan_tenure_months": 36.0, "num_active_loans": 1.0, "num_enquiries_6m": 1.0,
        "bank_account_age_months": 48.0, "loan_amount_requested": 150000.0,
        "behaviour_idx": 0.2, "employment_type": 0.0}
    from shared.types import compute_input_hash
    binding = env["client"].post("/v1/input-bindings", json={"application_id_hash":app_hash,
        "x_prime":compute_input_hash(features),"decision_id":decision_id},
        headers={"X-Lender-Key":"test-lender-secret"})
    assert binding.status_code == 200, binding.text
    return {"decision_id": decision_id, "application_id_hash": app_hash, "decision": decision, "features": features}


def proof_payload(policy, notice, proof_bytes=None, **overrides):
    from shared.types import ProofPayload
    proof_bytes = proof_bytes if proof_bytes is not None else b"SAKSHI_TEST_VALID_PROOF:fixture"
    import base64
    data = {"decision_id": notice["decision_id"], "policy_id": policy["policy_id"],
        "proof": base64.b64encode(proof_bytes).decode(),
        "public_inputs": {"policy_hash": policy["policy_hash"], "C": policy["model"]["commitment"],
            "X": __import__("shared.types", fromlist=["compute_input_hash"]).compute_input_hash(notice["features"]),
            "decision": notice["decision"], "threshold": 0.2,
            "epoch": int(datetime.now(timezone.utc).strftime("%Y%m%d"))}}
    data.update(overrides)
    return ProofPayload.model_validate(data)
