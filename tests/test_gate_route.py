"""Fail-closed gate and SLA state transition tests."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from node.models import Decision
from node.services.sla_monitor import expire_due_decisions
from tests.conftest import register_model, register_policy, create_notice, proof_payload


def test_gate_returns_verified_after_valid_proof(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    p=proof_payload(policy,notice)
    r=env["client"].post("/v1/proofs",json=p.model_dump(mode="json"),headers={
        "X-Sakshi-Key":"test-sidecar-secret","Idempotency-Key":"gate-valid-proof-001"})
    assert r.status_code == 202
    gate=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert gate["status"] == "VERIFIED"


def test_gate_returns_failed_for_invalid_proof(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    p=proof_payload(policy,notice,proof_bytes=b"garbage")
    env["client"].post("/v1/proofs",json=p.model_dump(mode="json"),headers={
        "X-Sakshi-Key":"test-sidecar-secret","Idempotency-Key":"gate-invalid-proof-001"})
    gate=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert gate["status"] == "FAILED"
    assert gate["failure_reason"] == "INVALID_PROOF"


def test_gate_pending_before_proof(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    gate=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert gate["status"] == "NOTICE_RECEIVED"


def test_sla_expiration_is_persisted_and_logged(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    with env["session"]() as db:
        d=db.get(Decision,notice["decision_id"])
        d.sla_deadline=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(seconds=1)
        db.commit()
    assert expire_due_decisions() == 1
    gate=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert gate["status"] == "EXPIRED"
    assert gate["ledger_seq"] == 1
