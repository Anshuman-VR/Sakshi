"""Input-binding adapter client; shared hashing contract is used by Lender Node."""
import os
import math
from shared.types import FEATURE_ORDER
import httpx
from shared.types import compute_input_hash


def canonical_input_commitment(features: dict[str, float]) -> str:
    if set(features) != set(FEATURE_ORDER):
        raise ValueError("Features must contain every canonical FEATURE_ORDER field exactly once")
    for name, value in features.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"Feature {name!r} must be a finite numeric value")
    return compute_input_hash(features)


async def bind(application_id_hash: str, features: dict[str, float], lender_node_url: str,
               lender_admin_key: str, decision_id: str | None = None) -> dict:
    x_prime = canonical_input_commitment(features)
    payload = {"application_id_hash": application_id_hash, "x_prime": x_prime}
    if decision_id:
        payload["decision_id"] = decision_id
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        response = await client.post(f"{lender_node_url.rstrip('/')}/v1/input-bindings",
            json=payload, headers={"X-Lender-Key": lender_admin_key})
        response.raise_for_status()
        return response.json()
