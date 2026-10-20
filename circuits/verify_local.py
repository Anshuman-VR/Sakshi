"""Local proof verifier for native EZKL proofs and clearly labelled test attestations.

A mock attestation is only a signed development statement; it does not prove
that a model ran correctly and must never be accepted as production ZK evidence.
"""
from __future__ import annotations

import base64
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from circuits.prove import (
    BACKEND_PATH, COMPILED_PATH, SETTINGS_PATH, SRS_PATH, VK_PATH, MOCK_PUBLIC_KEY_PATH,
    decode_ezkl_probability, decision_from_quantized_score,
)
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

    if not all(path.is_file() for path in (COMPILED_PATH, VK_PATH, SETTINGS_PATH, BACKEND_PATH, SRS_PATH)):
        return False
    try:
        backend_metadata = json.loads(BACKEND_PATH.read_text(encoding="utf-8"))
        if backend_metadata.get("backend") != "ezkl" or backend_metadata.get("statement_binding") != "model-inference-only":
            return False
        if backend_metadata.get("model_commitment") and payload.public_inputs.C != backend_metadata["model_commitment"]:
            return False
        # Validate the metadata against the signed policy and the exact compiled circuit.
        policy_path = Path(__file__).resolve().parents[1] / "policy" / "example_policy.json"
        if not policy_path.is_file():
            return False
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        from policy.sign import verify_policy
        pub = payload.public_inputs
        if not verify_policy(policy):
            return False
        if (
            payload.policy_id != policy.get("policy_id")
            or pub.policy_hash != policy.get("policy_hash")
            or pub.C != policy.get("model_commitment")
            or abs(float(pub.threshold) - float(policy.get("decision_threshold"))) > 1e-9
            or str(policy.get("circuit_hash", "")).removeprefix("0x") != backend_metadata.get("circuit_hash")
        ):
            return False
        if len(pub.X) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in pub.X):
            return False
        import ezkl  # type: ignore[import-not-found]
        proof_document = json.loads(proof_bytes.decode("utf-8"))
        instances = proof_document.get("instances")
        if not instances or not instances[0]:
            return False
        with tempfile.NamedTemporaryFile(prefix="sakshi-verify-", suffix=".proof", dir=str(COMPILED_PATH.parent), delete=False) as stream:
            proof_path = Path(stream.name)
            stream.write(proof_bytes)
        try:
            result = ezkl.verify(
                str(proof_path), str(SETTINGS_PATH), str(VK_PATH), srs_path=str(SRS_PATH)
            )
        finally:
            proof_path.unlink(missing_ok=True)
        if not bool(result):
            return False
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        quantized_score, _, output_scale = decode_ezkl_probability(str(instances[0][0]), settings)
        expected_decision = decision_from_quantized_score(
            quantized_score, payload.public_inputs.threshold, output_scale
        )
        # This binds the claimed decision to the proof's public score. The signed
        # policy hash/threshold and input SHA-256 X still require external policy
        # validation; they are not all in this ONNX circuit's public statement.
        return expected_decision == payload.public_inputs.decision
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
