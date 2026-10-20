"""Tests for the live demo application route (/v1/demo/apply)."""
import pytest
from fastapi.testclient import TestClient
from node.main import app
from node.database import get_db
from node.config import config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from node.models import Base
from pydantic import SecretStr


@pytest.fixture
def demo_client():
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
    config.environment = "test"
    config.mock_verify = True
    config.sidecar_api_key = SecretStr("test-sidecar-secret")
    config.lender_admin_key = SecretStr("test-lender-secret")
    
    with TestClient(app) as client:
        yield client
        
    app.dependency_overrides.clear()
    engine.dispose()


def test_demo_apply_prime_borrower(demo_client):
    res = demo_client.post("/v1/demo/apply", json={"persona": "priya"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "VERIFIED"
    assert data["decision"] == 1
    assert data["decision_label"] == "APPROVED"
    assert data["ledger_seq"] is not None
    assert data["failure_reason"] is None


def test_demo_apply_subprime_borrower(demo_client):
    res = demo_client.post("/v1/demo/apply", json={"persona": "rahul"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "VERIFIED"
    assert data["decision"] == 0
    assert data["decision_label"] == "REJECTED"
    assert data["ledger_seq"] is not None


def test_demo_apply_tamper_model_fails(demo_client):
    res = demo_client.post("/v1/demo/apply", json={"persona": "priya", "tamper": "model"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "FAILED"
    assert data["failure_reason"] == "MODEL_MISMATCH"


def test_demo_apply_tamper_threshold_fails(demo_client):
    res = demo_client.post("/v1/demo/apply", json={"persona": "priya", "tamper": "threshold"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "FAILED"
    assert data["failure_reason"] == "THRESHOLD_MISMATCH"


def test_demo_apply_tamper_input_binding_fails(demo_client):
    res = demo_client.post("/v1/demo/apply", json={"persona": "priya", "tamper": "input"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "FAILED"
    assert data["failure_reason"] == "BINDING_MISMATCH"
