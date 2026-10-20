from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from sidecar import database, main, outbox, prover_worker
from sidecar.models import Base, OutboxMessage, ProverJob, utcnow
from shared.types import FEATURE_ORDER, compute_application_hash


FEATURES = {
    "bureau_score": 750.0, "monthly_income": 80000.0, "foir": 0.30,
    "loan_tenure_months": 36.0, "num_active_loans": 1.0,
    "num_enquiries_6m": 0.0, "bank_account_age_months": 60.0,
    "loan_amount_requested": 100000.0, "behaviour_idx": 0.20, "employment_type": 0.0,
}


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    engine = database.reset_engine_for_tests(str(tmp_path / "sidecar-test.db"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(database, "SessionLocal", factory)
    monkeypatch.setattr(main, "SessionLocal", factory)
    monkeypatch.setattr(outbox, "SessionLocal", factory)
    monkeypatch.setattr(prover_worker, "SessionLocal", factory)
    yield factory
    engine.dispose()


def event_body(decision_id="d_api_1"):
    return {
        "decision_id": decision_id,
        "application_id": "application-private-id",
        "policy_id": "pol_demo_v1",
        "features": dict(FEATURES),
        "decision": 1,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def test_health_and_metrics(isolated_db):
    with TestClient(main.create_app(start_worker=False)) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert 'sakshi_queue_depth 0' in metrics.text


def test_submit_decision_event_is_queued_and_idempotent(isolated_db):
    with TestClient(main.create_app(start_worker=False)) as client:
        response = client.post("/v1/prove", json=event_body())
        assert response.status_code == 202
        result = response.json()
        assert result["status"] == "QUEUED"
        assert result["job_id"]
        status = client.get(f"/v1/jobs/{result['job_id']}")
        assert status.status_code == 200
        assert status.json()["status"] == "QUEUED"
        replay = client.post("/v1/prove", json=event_body())
        assert replay.status_code == 202
        assert replay.headers.get("Idempotency-Replayed") == "true"
        assert replay.json()["job_id"] == result["job_id"]


def test_duplicate_decision_id_with_changed_content_conflicts(isolated_db):
    with TestClient(main.create_app(start_worker=False)) as client:
        assert client.post("/v1/prove", json=event_body()).status_code == 202
        changed = event_body()
        changed["decision"] = 0
        response = client.post("/v1/prove", json=changed)
        assert response.status_code == 409


def test_invalid_features_rejected(isolated_db):
    with TestClient(main.create_app(start_worker=False)) as client:
        invalid = event_body()
        invalid["features"].pop(FEATURE_ORDER[0])
        response = client.post("/v1/prove", json=invalid)
        assert response.status_code == 422


def test_unknown_job_returns_404(isolated_db):
    with TestClient(main.create_app(start_worker=False)) as client:
        assert client.get("/v1/jobs/not-a-job").status_code == 404


def test_outbox_retries_then_marks_delivered(isolated_db, monkeypatch):
    import sidecar.config as config_module
    monkeypatch.setattr(config_module.config, "lender_node_url", "http://lender-node:8000")
    with isolated_db() as session:
        session.add(OutboxMessage(
            decision_id="d_outbox", target_endpoint="/v1/decisions",
            payload_json=json.dumps({"decision_id": "d_outbox"}), status="PENDING",
            attempts=0, next_retry_at=utcnow(),
        ))
        session.commit()

    calls = {"count": 0}
    async def handler(request):
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, json={"error": "try again"})
        return httpx.Response(202, json={"status": "accepted"})

    async def run_test():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await outbox.process_outbox(client=client)
            with isolated_db() as session:
                message = session.scalar(select(OutboxMessage).where(OutboxMessage.decision_id == "d_outbox"))
                assert message.status == "PENDING"
                assert message.attempts == 1
                message.next_retry_at = utcnow()
                session.commit()
            await outbox.process_outbox(client=client)
        with isolated_db() as session:
            message = session.scalar(select(OutboxMessage).where(OutboxMessage.decision_id == "d_outbox"))
            assert message.status == "DELIVERED"
            assert message.attempts == 2
    asyncio.run(run_test())


def test_notice_is_delivered_before_proof(isolated_db):
    with isolated_db() as session:
        session.add_all([
            OutboxMessage(decision_id="d_order", target_endpoint="/v1/decisions", payload_json="{}", status="PENDING", attempts=0, next_retry_at=utcnow()),
            OutboxMessage(decision_id="d_order", target_endpoint="/v1/proofs", payload_json="{}", status="PENDING", attempts=0, next_retry_at=utcnow()),
        ])
        session.commit()
    seen = []
    async def handler(request):
        seen.append(request.url.path)
        return httpx.Response(202)
    async def run_test():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await outbox.process_outbox(client=client)
            assert seen == ["/v1/decisions", "/v1/proofs"]
            with isolated_db() as session:
                notice = session.scalar(select(OutboxMessage).where(OutboxMessage.target_endpoint == "/v1/decisions"))
                proof = session.scalar(select(OutboxMessage).where(OutboxMessage.target_endpoint == "/v1/proofs"))
                assert notice.status == "DELIVERED"
                assert proof.status == "DELIVERED"
    asyncio.run(run_test())


def test_worker_persists_proof_and_minimised_notice(isolated_db, monkeypatch):
    # Force the explicit local mock backend; no network call is made by this test.
    import sidecar.config as config_module
    monkeypatch.setattr(config_module.config, "allow_mock_proofs", True)
    with isolated_db() as session:
        session.add(ProverJob(
            job_id="job_worker_1", decision_id="d_worker_1", application_id_hash=compute_application_hash("raw-app-id-must-not-leak"),
            policy_id="pol_demo_v1", status="QUEUED",
            features_json=json.dumps({name: FEATURES[name] for name in FEATURE_ORDER}, separators=(",", ":")),
            decision=1, created_at=utcnow(), updated_at=utcnow(),
        ))
        session.commit()
    async def run_test():
        assert await prover_worker.process_one_job()
    asyncio.run(run_test())
    with isolated_db() as session:
        job = session.get(ProverJob, "job_worker_1")
        assert job.status == "PROVING"
        assert job.proof_payload_json
        assert job.features_json == "{}"  # Raw features are scrubbed after proof creation.
        assert job.application_id_hash == compute_application_hash("raw-app-id-must-not-leak")
        notice = session.scalar(select(OutboxMessage).where(OutboxMessage.target_endpoint == "/v1/decisions"))
        proof = session.scalar(select(OutboxMessage).where(OutboxMessage.target_endpoint == "/v1/proofs"))
        assert notice and proof
        assert "raw-app-id-must-not-leak" not in notice.payload_json
        assert "monthly_income" not in notice.payload_json
        assert notice.payload_json.find("application_id_hash") >= 0
