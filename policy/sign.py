"""Canonical dual-party Ed25519 policy signing and verification.

For a real deployment, lender and LSP keys must be provisioned and held by the
respective parties. The default key paths are local demo-only keys and are not
an institutional trust anchor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
KEY_DIR = ROOT / "circuits" / "artifacts"
POLICY_PATH = Path(__file__).resolve().parent / "example_policy.json"


def canonical_policy_bytes(policy: dict[str, Any]) -> bytes:
    """Canonical JSON; signatures and derived policy_hash are excluded."""
    unsigned = {k: v for k, v in policy.items() if k not in {"lsp_sig", "lender_sig", "policy_hash", "signing_mode"}}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _load_or_create_private_key(path: Path) -> Ed25519PrivateKey:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise TypeError(f"Expected Ed25519 private key at {path}")
        return key
    key = Ed25519PrivateKey.generate()
    path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


def _public_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def generate_signed_policy(
    model_commitment: str,
    circuit_hash: str,
    *,
    policy_path: str | os.PathLike[str] | None = None,
    lsp_private_key_path: str | os.PathLike[str] | None = None,
    lender_private_key_path: str | os.PathLike[str] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Create a demo policy signed independently by LSP and lender keypairs."""
    if not model_commitment or not circuit_hash:
        raise ValueError("model_commitment and circuit_hash are required")
    lsp_path = Path(lsp_private_key_path) if lsp_private_key_path else KEY_DIR / "demo_lsp_policy_ed25519.pem"
    lender_path = Path(lender_private_key_path) if lender_private_key_path else KEY_DIR / "demo_lender_policy_ed25519.pem"
    lsp_key = _load_or_create_private_key(lsp_path)
    lender_key = _load_or_create_private_key(lender_path)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    unsigned: dict[str, Any] = {
        "policy_id": "pol_meridian_quickfin_v1",
        "version": 1,
        "lender_id": "meridian_digital",
        "lsp_id": "quick_fincorp",
        "product": "personal_loan",
        "model_commitment": model_commitment,
        "circuit_hash": circuit_hash,
        "feature_schema_hash": hashlib.sha256(json.dumps(
            ["bureau_score", "monthly_income", "foir", "loan_tenure_months", "num_active_loans",
             "num_enquiries_6m", "bank_account_age_months", "loan_amount_requested", "behaviour_idx", "employment_type"],
            separators=(",", ":"), ensure_ascii=True).encode()).hexdigest(),
        "decision_threshold": 0.500,
        "fixed_point_scale": 1024,
        "hard_rules": [
            {"id": "R1", "feature": "bureau_score", "op": "gte", "value": 600.0},
            {"id": "R2", "feature": "foir", "op": "lte", "value": 0.65},
        ],
        "proof_sla_minutes": 10,
        "valid_from": now.isoformat().replace("+00:00", "Z"),
        "valid_to": (now + timedelta(days=365)).isoformat().replace("+00:00", "Z"),
        "lsp_pubkey": _public_hex(lsp_key),
        "lender_pubkey": _public_hex(lender_key),
    }
    canonical = canonical_policy_bytes(unsigned)
    policy = {
        **unsigned,
        "lsp_sig": lsp_key.sign(canonical).hex(),
        "lender_sig": lender_key.sign(canonical).hex(),
        "policy_hash": hashlib.sha256(canonical).hexdigest(),
        "signing_mode": "demo-local-keys-not-production-trust",
    }
    # signing_mode is metadata, not part of the signed policy contract or hash.
    destination = Path(policy_path) if policy_path else POLICY_PATH
    if persist:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return policy


def sign_policy_document(policy: dict[str, Any], signer: str, private_key_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Sign finalized policy bytes using one party's provisioned private key.

    Both public keys must already be in the agreed document before either party
    signs. This ensures the LSP and lender sign exactly the same canonical bytes.
    """
    if signer not in {"lsp", "lender"}:
        raise ValueError("signer must be 'lsp' or 'lender'")
    key = _load_or_create_private_key(Path(private_key_path))
    expected_pub = _public_hex(key)
    if policy.get(f"{signer}_pubkey") != expected_pub:
        raise ValueError(f"{signer}_pubkey in policy does not match supplied private key")
    result = dict(policy)
    canonical = canonical_policy_bytes(result)
    result[f"{signer}_sig"] = key.sign(canonical).hex()
    result["policy_hash"] = hashlib.sha256(canonical).hexdigest()
    return result


def verify_policy(policy: dict[str, Any]) -> bool:
    """Verify both Ed25519 signatures and the derived policy hash."""
    try:
        canonical = canonical_policy_bytes(policy)
        expected_hash = hashlib.sha256(canonical).hexdigest()
        if policy.get("policy_hash") != expected_hash:
            return False
        for party in ("lsp", "lender"):
            pub_bytes = bytes.fromhex(policy[f"{party}_pubkey"])
            sig_bytes = bytes.fromhex(policy[f"{party}_sig"])
            Ed25519PublicKey.from_public_bytes(pub_bytes).verify(sig_bytes, canonical)
        # Structural check against the shared contract without modifying it.
        from shared.types import PolicyDocument
        PolicyDocument.model_validate({k: v for k, v in policy.items() if k not in {"policy_hash", "signing_mode"}})
        return True
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-commitment", default="0x" + hashlib.sha256(b"SAKSHI_DEMO_ONLY_MODEL_COMMITMENT_NOT_PRODUCTION").hexdigest())
    parser.add_argument("--circuit-hash", default="0x" + hashlib.sha256(b"SAKSHI_DEMO_ONLY_CIRCUIT_NOT_PRODUCTION").hexdigest())
    parser.add_argument("--output", default=str(POLICY_PATH))
    args = parser.parse_args()
    policy = generate_signed_policy(args.model_commitment, args.circuit_hash, policy_path=args.output)
    print(f"Policy written to {args.output}")
    print(f"Policy hash: {policy['policy_hash']}")
    print(f"Dual signatures valid: {verify_policy(policy)}")
    print("WARNING: default signing keys are local demo keys, not production identity keys.")


if __name__ == "__main__":
    main()
