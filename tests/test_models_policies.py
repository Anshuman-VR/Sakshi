"""Registration governance and signature validation tests."""
from tests.conftest import register_model, register_policy


def test_model_is_not_auto_approved(environment):
    # Register helper performs approval, so inspect the state immediately after
    # registration using a separately signed model payload.
    import base64
    from node.services.crypto import model_registration_signing_payload
    env=environment
    data={"commitment":"9"*64,"circuit_hash":"8"*64,"vk":base64.b64encode(b'{"vk":1}').decode(),
      "feature_schema_hash":"7"*64,"parity_report":{"float_auc":0.8,"quantized_auc":0.79,"agreement_pct":99.0,"test_samples":10},
      "lsp_pubkey":env["lsp_public"],"lsp_sig":""}
    data["lsp_sig"]=env["lsp_private"].sign(model_registration_signing_payload(data)).hex()
    r=env["client"].post("/v1/models",json=data,headers={"X-Sakshi-Key":"test-sidecar-secret"})
    assert r.status_code==201
    assert r.json()["status"]=="PENDING_APPROVAL"


def test_invalid_model_signature_rejected(environment):
    import base64
    env=environment
    data={"commitment":"9"*64,"circuit_hash":"8"*64,"vk":base64.b64encode(b'{"vk":1}').decode(),
      "feature_schema_hash":"7"*64,"parity_report":{"float_auc":0.8,"quantized_auc":0.79,"agreement_pct":99.0,"test_samples":10},
      "lsp_pubkey":env["lsp_public"],"lsp_sig":"00"*64}
    r=env["client"].post("/v1/models",json=data,headers={"X-Sakshi-Key":"test-sidecar-secret"})
    assert r.status_code==400 and r.json()["detail"]=="INVALID_SIGNATURE"


def test_dashboard_never_invents_latency(environment):
    response=environment["client"].get("/v1/dashboard/summary")
    assert response.status_code==200
    data=response.json()
    assert data["proof_latency_p50_ms"] is None
    assert data["proof_latency_p95_ms"] is None
    assert data["total_decisions"]==0


def test_model_revocation_revokes_linked_policy(environment):
    from node.services.crypto import lender_approval_payload
    env=environment; model=register_model(env); policy=register_policy(env,model)
    signature=env["lender_private"].sign(lender_approval_payload(model["model_id"],model["commitment"],
        "REVOKE",model["circuit_hash"],model["feature_schema_hash"])).hex()
    response=env["client"].post(f"/v1/models/{model['model_id']}/revoke",json={
        "lender_sig":signature,"lender_pubkey":env["lender_public"]},
        headers={"X-Lender-Key":"test-lender-secret"})
    assert response.status_code==200
    assert response.json()["status"]=="REVOKED"
    policy_response=env["client"].get(f"/v1/policies/{policy['policy_id']}")
    assert policy_response.status_code==200
    with env["session"]() as db:
        from node.models import Policy
        assert db.get(Policy,policy["policy_id"]).status=="REVOKED"
