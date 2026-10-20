"""V1-V9 integration/tamper tests for the Lender Node."""
from datetime import datetime, timezone
from tests.conftest import register_model, register_policy, create_notice, proof_payload


def submit(env, payload, key="idempotency-test-key"):
    r = env["client"].post("/v1/proofs", json=payload.model_dump(mode="json"),
        headers={"X-Sakshi-Key": "test-sidecar-secret", "Idempotency-Key": key})
    assert r.status_code == 202, r.text
    return r.json()


def test_honest_flow_verifies_and_ledger_records(environment):
    env = environment; model = register_model(env); policy = register_policy(env, model)
    notice = create_notice(env, policy)
    response = submit(env, proof_payload(policy, notice))
    status = env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert status["status"] == "VERIFIED"
    assert status["ledger_seq"] == 1
    assert response["status"] == "PENDING"
    assert env["client"].get("/v1/ledger/export", headers={"X-Lender-Key": "test-lender-secret"}).json()["chain_valid"] is True


def test_model_mismatch_fails_v2(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    payload=proof_payload(policy,notice); payload.public_inputs.C="f"*64
    submit(env,payload)
    r=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert (r["status"],r["failure_reason"]) == ("FAILED","MODEL_MISMATCH")


def test_policy_hash_mismatch_fails_v3(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    payload=proof_payload(policy,notice); payload.public_inputs.policy_hash="e"*64
    submit(env,payload)
    r=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert r["failure_reason"] == "POLICY_HASH_MISMATCH"


def test_threshold_mismatch_fails_v4(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    payload=proof_payload(policy,notice); payload.public_inputs.threshold=0.05
    submit(env,payload)
    r=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert r["failure_reason"] == "THRESHOLD_MISMATCH"


def test_invalid_epoch_fails_v5(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    payload=proof_payload(policy,notice); payload.public_inputs.epoch=20000101
    submit(env,payload)
    r=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert r["failure_reason"] == "WINDOW_INVALID"


def test_decision_mismatch_fails_v7(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy,decision=1)
    payload=proof_payload(policy,notice); payload.public_inputs.decision=0
    submit(env,payload)
    r=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert r["failure_reason"] == "DECISION_MISMATCH"


def test_invalid_proof_bytes_fail_v8(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    payload=proof_payload(policy,notice,proof_bytes=b"random bytes not a proof")
    submit(env,payload)
    r=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert r["failure_reason"] == "INVALID_PROOF"


def test_public_hard_rule_violation_fails_v9(environment):
    env=environment; model=register_model(env)
    policy=register_policy(env,model,hard_rules=[{"id":"R1","feature":"decision","op":"eq","value":0}])
    notice=create_notice(env,policy,decision=1)
    submit(env,proof_payload(policy,notice))
    r=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert r["failure_reason"] == "HARD_RULE_VIOLATION"


def test_replay_rejected_across_decisions(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model)
    notice1=create_notice(env,policy,decision_id="d_replay_1",app_id="app-1")
    payload=proof_payload(policy,notice1)
    submit(env,payload,"replay-key-0001")
    notice2=create_notice(env,policy,decision_id="d_replay_2",app_id="app-2")
    payload2=proof_payload(policy,notice2)
    payload2.proof=payload.proof
    submit(env,payload2,"replay-key-0002")
    r=env["client"].get(f"/v1/decisions/{notice2['decision_id']}/status").json()
    assert (r["status"],r["failure_reason"]) == ("FAILED","REPLAY")


def test_idempotency_key_reuse_with_different_body_rejected(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    payload=proof_payload(policy,notice)
    submit(env,payload,"same-idempotency-key")
    payload2=proof_payload(policy,notice,proof_bytes=b"different proof")
    r=env["client"].post("/v1/proofs",json=payload2.model_dump(mode="json"),
        headers={"X-Sakshi-Key":"test-sidecar-secret","Idempotency-Key":"same-idempotency-key"})
    assert r.status_code == 409


def test_gate_unknown_decision_fails_closed(environment):
    r=environment["client"].get("/v1/decisions/not-real/status")
    assert r.status_code == 200
    assert r.json()["status"] == "NOT_FOUND"


def test_auth_required_for_sidecar(environment):
    r=environment["client"].post("/v1/decisions",json={})
    assert r.status_code == 401


def test_missing_policy_fails_v1(environment):
    from node.services.verifier import VerifierEngine
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    payload=proof_payload(policy,notice); payload.policy_id="does_not_exist"
    with env["session"]() as db:
        result=VerifierEngine.run_pipeline(db,payload,verification_id="v_missing_policy")
    assert result.status=="FAILED"
    assert result.reason=="V1_POLICY_NOT_FOUND"


def test_input_commitment_mismatch_fails_closed(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    payload=proof_payload(policy,notice,proof_bytes=b"SAKSHI_TEST_VALID_PROOF:binding-mismatch")
    payload.public_inputs.X="f"*64
    submit(env,payload,"binding-mismatch-key")
    gate=env["client"].get(f"/v1/decisions/{notice['decision_id']}/status").json()
    assert gate["status"]=="FAILED"
    assert gate["failure_reason"]=="BINDING_MISMATCH"


def test_binding_api_rejects_raw_features(environment):
    env=environment; model=register_model(env); policy=register_policy(env,model); notice=create_notice(env,policy)
    r=env["client"].post("/v1/input-bindings",json={"application_id_hash":notice["application_id_hash"],
        "features":notice["features"],"decision_id":notice["decision_id"]},
        headers={"X-Lender-Key":"test-lender-secret"})
    assert r.status_code==422
