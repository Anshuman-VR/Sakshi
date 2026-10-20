"""Local proof verifier for native EZKL proofs and clearly labelled test attestations.

A mock attestation is only a signed development statement; it does not prove
that a model ran correctly and must never be accepted as production ZK evidence.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from circuits.prove import BACKEND_PATH, COMPILED_PATH, SETTINGS_PATH, VK_PATH, MOCK_PUBLIC_KEY_PATH
from shared.types import ProofPayload, compute_input_hash


def verify_local(payload: ProofPayload | dict[str, Any], *, allow_mock: bool = True) -> bool:
    if isinstance(payload, dict):
        payload = ProofPayload.model_validate(payload)
    try:
        proof_bytes = base64.b64decode(payload.proof, validate=True)
    except Exception:
        return False

    try:
        envelope = json.loads(proof_bytes.decode("utf-8"))
    except Exception:
        envelope = None
    if isinstance(envelope, dict) and envelope.get("format") == "SAKSHI_MOCK_ATTESTATION_NOT_ZK_V1":
        if not allow_mock:
            return False
        try:
            from cryptography.hazmat.primitives import serialization
            statement = base64.b64decode(envelope["statement_b64"], validate=True)
            signature = base64.b64decode(envelope["signature_b64"], validate=True)
            # Trust the locally provisioned public key, never a key supplied only by the proof.
            if not MOCK_PUBLIC_KEY_PATH.is_file():
                return False
            public = serialization.load_pem_public_key(MOCK_PUBLIC_KEY_PATH.read_bytes())
            embedded_public = serialization.load_pem_public_key(envelope["verification_key_pem"].encode("ascii"))
            if public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw) != embedded_public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw):
                return False
            public.verify(signature, statement)
            statement_data = json.loads(statement)
            pub = payload.public_inputs
            return (
                statement_data.get("decision_id") == payload.decision_id
                and statement_data.get("policy_id") == payload.policy_id
                and statement_data.get("policy_hash") == pub.policy_hash
                and statement_data.get("C") == pub.C
                and statement_data.get("X") == pub.X
                and statement_data.get("decision") == pub.decision
                and float(statement_data.get("threshold")) == float(pub.threshold)
                and int(statement_data.get("epoch")) == pub.epoch
            )
        except Exception:
            return False

    if not all(path.is_file() for path in (COMPILED_PATH, VK_PATH, SETTINGS_PATH, BACKEND_PATH)):
        return False
    try:
        backend_metadata = json.loads(BACKEND_PATH.read_text(encoding="utf-8"))
        if backend_metadata.get("backend") != "ezkl" or backend_metadata.get("statement_binding") != "full-policy-binding":
            return False
        import ezkl  # type: ignore[import-not-found]
        proof_path = COMPILED_PATH.parent / "_verify_local.proof"
        proof_path.write_bytes(proof_bytes)
        result = ezkl.verify(str(proof_path), str(VK_PATH), str(SETTINGS_PATH))
        return bool(result)
    except Exception:
        return False


def verify_mock_signature_only(proof_b64: str) -> bool:
    """Diagnostic helper: validates mock signature only, not proof semantics."""
    try:
        envelope = json.loads(base64.b64decode(proof_b64, validate=True).decode("utf-8"))
        from cryptography.hazmat.primitives import serialization
        statement = base64.b64decode(envelope["statement_b64"], validate=True)
        signature = base64.b64decode(envelope["signature_b64"], validate=True)
        if not MOCK_PUBLIC_KEY_PATH.is_file():
            return False
        public = serialization.load_pem_public_key(MOCK_PUBLIC_KEY_PATH.read_bytes())
        embedded_public = serialization.load_pem_public_key(envelope["verification_key_pem"].encode("ascii"))
        if public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw) != embedded_public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw):
            return False
        public.verify(signature, statement)
        return True
    except Exception:
        return False
