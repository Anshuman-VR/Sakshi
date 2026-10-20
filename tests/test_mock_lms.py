"""Unit tests for the fail-closed LMS gate; no live service is contacted."""
import asyncio

import httpx
import pytest

from mock_lms.disbursal_gate import attempt_loan_disbursal


class FakeResponse:
    def __init__(self, status_code=200, body=None, invalid_json=False):
        self.status_code = status_code
        self.body = body
        self.invalid_json = invalid_json

    def json(self):
        if self.invalid_json:
            raise ValueError("invalid json")
        return self.body


class FakeClient:
    response = FakeResponse()
    error = None
    requested_url = None

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        type(self).requested_url = url
        if type(self).error:
            raise type(self).error
        return type(self).response


def call(monkeypatch, response=None, error=None, decision_id="d_test"):
    FakeClient.response = response or FakeResponse()
    FakeClient.error = error
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    return asyncio.run(attempt_loan_disbursal("http://lender:8000/", decision_id, 150000))


def test_verified_allows_simulated_disbursal(monkeypatch):
    result = call(monkeypatch, FakeResponse(body={"status": "VERIFIED"}))
    assert result.disbursed is True
    assert result.status == "VERIFIED"
    assert result.disbursal_reference.startswith("SIM-NEFT-")


@pytest.mark.parametrize("status", ["NOTICE_RECEIVED", "FAILED", "EXPIRED", "NOT_FOUND", "PENDING", None, "verified"])
def test_any_status_other_than_exact_verified_holds(monkeypatch, status):
    result = call(monkeypatch, FakeResponse(body={"status": status}))
    assert result.disbursed is False
    assert result.disbursal_reference is None


def test_timeout_fails_closed(monkeypatch):
    result = call(monkeypatch, error=httpx.TimeoutException("timeout"))
    assert result.disbursed is False
    assert result.status == "GATE_OFFLINE"


def test_non_200_fails_closed(monkeypatch):
    result = call(monkeypatch, FakeResponse(status_code=503, body={"status": "VERIFIED"}))
    assert result.disbursed is False
    assert result.status == "VERIFIER_ERROR"


def test_invalid_json_fails_closed(monkeypatch):
    result = call(monkeypatch, FakeResponse(invalid_json=True))
    assert result.disbursed is False
    assert result.status == "INVALID_VERIFIER_RESPONSE"


def test_decision_id_is_url_encoded(monkeypatch):
    call(monkeypatch, FakeResponse(body={"status": "VERIFIED"}), decision_id="d/unsafe")
    assert "/d%2Funsafe/status" in FakeClient.requested_url
