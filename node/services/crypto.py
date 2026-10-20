"""Canonical encoding and Ed25519 helpers shared by registration and policy APIs."""
import base64
import binascii
import hashlib
import json
from typing import Any
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_hex(value: str) -> bytes:
    try:
        return bytes.fromhex(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Expected hexadecimal encoding") from exc


def decode_b64(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise ValueError("Expected valid base64 encoding") from exc


def verify_ed25519(public_key_hex: str, signature_hex: str, message: bytes) -> bool:
    try:
        key = Ed25519PublicKey.from_public_bytes(decode_hex(public_key_hex))
        signature = decode_hex(signature_hex)
        key.verify(signature, message)
        return True
    except (ValueError, InvalidSignature, TypeError):
        return False


def model_registration_signing_payload(payload: dict) -> bytes:
    unsigned = {k: v for k, v in payload.items() if k != "lsp_sig"}
    return canonical_json(unsigned).encode("utf-8")


def policy_signing_payload(payload: dict) -> bytes:
    unsigned = {k: v for k, v in payload.items() if k not in {"lsp_sig", "lender_sig"}}
    return canonical_json(unsigned).encode("utf-8")


def lender_approval_payload(model_id: str, commitment: str, action: str = "APPROVE",
                            circuit_hash: str = "", feature_schema_hash: str = "") -> bytes:
    return canonical_json({"action": action, "commitment": commitment,
                           "circuit_hash": circuit_hash, "feature_schema_hash": feature_schema_hash,
                           "model_id": model_id}).encode("utf-8")
