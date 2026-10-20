"""Decision notice lifecycle and SLA deadline contract tests."""
from datetime import datetime, timedelta, timezone
import hashlib

from tests.conftest import register_model, register_policy


def test_sla_deadline_is_based_on_notice_timestamp(environment):
    model = register_model(environment)
    policy = register_policy(environment, model)
    decision_ts = datetime.now(timezone.utc) - timedelta(minutes=2)
    app_hash = hashlib.sha256(b"sla-deadline-app").hexdigest()
    response = environment["client"].post(
        "/v1/decisions",
        json={
            "decision_id": "d_sla_timestamp_contract",
            "application_id_hash": app_hash,
            "policy_id": policy["policy_id"],
            "decision": 1,
            "ts": decision_ts.isoformat(),
        },
        headers={"X-Sakshi-Key": "test-sidecar-secret"},
    )
    assert response.status_code == 202, response.text
    deadline = datetime.fromisoformat(response.json()["sla_deadline"])
    expected = decision_ts.replace(tzinfo=None) + timedelta(minutes=10)
    assert abs((deadline - expected).total_seconds()) < 0.01


def test_notice_timestamp_far_in_future_is_rejected(environment):
    model = register_model(environment)
    policy = register_policy(environment, model)
    future_ts = datetime.now(timezone.utc) + timedelta(minutes=10)
    response = environment["client"].post(
        "/v1/decisions",
        json={
            "decision_id": "d_future_timestamp_contract",
            "application_id_hash": hashlib.sha256(b"future-app").hexdigest(),
            "policy_id": policy["policy_id"],
            "decision": 1,
            "ts": future_ts.isoformat(),
        },
        headers={"X-Sakshi-Key": "test-sidecar-secret"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "DECISION_TIMESTAMP_IN_FUTURE"
