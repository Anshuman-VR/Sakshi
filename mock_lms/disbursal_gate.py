"""Fail-closed disbursal gate for the Sakshi demo LMS.

This module simulates a disbursal decision only; it does not move real funds.
The lender verifier is authoritative. Only the exact status ``VERIFIED`` can
produce ``disbursed=True``. Every unknown/error state is held.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote

import httpx
from pydantic import BaseModel


class DisbursalResult(BaseModel):
    decision_id: str
    disbursed: bool
    status: str
    failure_reason: Optional[str] = None
    disbursal_reference: Optional[str] = None


async def attempt_loan_disbursal(
    lender_node_url: str,
    decision_id: str,
    amount: float,
    *,
    timeout_seconds: float = 4.0,
) -> DisbursalResult:
    """Check verifier status and return a simulated disbursal outcome.

    ``amount`` is accepted for LMS interface compatibility. No funds are moved.
    Network errors, malformed responses, non-200 responses, missing statuses,
    and any status other than the exact string ``VERIFIED`` fail closed.
    """
    del amount  # Explicitly a simulation: this module never transfers money.
    safe_id = quote(decision_id, safe="")
    url = f"{lender_node_url.rstrip('/')}/v1/decisions/{safe_id}/status"
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url)
    except (httpx.HTTPError, TimeoutError, OSError) as exc:
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status="GATE_OFFLINE",
            failure_reason=f"Fail-closed: verifier unreachable; funds held ({type(exc).__name__}).",
        )
    except Exception as exc:  # defensive: all unexpected transport failures hold funds
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status="GATE_OFFLINE",
            failure_reason=f"Fail-closed: verifier request failed ({type(exc).__name__}).",
        )

    if response.status_code != 200:
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status="NOT_FOUND" if response.status_code == 404 else "VERIFIER_ERROR",
            failure_reason=f"Verifier returned HTTP {response.status_code}; disbursal held.",
        )

    try:
        payload = response.json()
    except (ValueError, TypeError):
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status="INVALID_VERIFIER_RESPONSE",
            failure_reason="Verifier response was not valid JSON; disbursal held.",
        )

    if not isinstance(payload, dict):
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status="INVALID_VERIFIER_RESPONSE",
            failure_reason="Verifier response was not an object; disbursal held.",
        )

    status = payload.get("status")
    if status == "VERIFIED":
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=True,
            status="VERIFIED",
            disbursal_reference=f"SIM-NEFT-{decision_id}-SUCCESS",
        )
    if status == "NOTICE_RECEIVED":
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status="PENDING_PROOF",
            failure_reason="Awaiting proof verification. Disbursal held.",
        )

    # Includes FAILED, EXPIRED, NOT_FOUND, null, and unknown future states.
    reason = payload.get("failure_reason")
    return DisbursalResult(
        decision_id=decision_id,
        disbursed=False,
        status=status if isinstance(status, str) and status else "UNKNOWN_STATUS",
        failure_reason=f"Disbursal blocked by verifier status {status!r}." + (f" {reason}" if reason else ""),
    )
