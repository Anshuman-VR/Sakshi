"""Scorecard witness/proof generation.

Native EZKL output is attempted first. The fallback is a signed development
attestation, explicitly NOT a zero-knowledge proof; verify_local.py checks it
only to make local integration/tamper tests deterministic.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import tempfile
from pathlib import Path
from typing import Any

from shared.types import FEATURE_ORDER, FIXED_POINT_SCALE, ProofPayload, PublicInputs, compute_input_hash, today_epoch

ROOT = Path(__file__).resolve().parents[1]
CIRCUITS_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = CIRCUITS_DIR / "artifacts"
COMPILED_PATH = ARTIFACTS_DIR / "scorecard.compiled"
VK_PATH = ARTIFACTS_DIR / "scorecard.vk"
PK_PATH = ARTIFACTS_DIR / "scorecard.pk"
SETTINGS_PATH = CIRCUITS_DIR / "settings.json"
BACKEND_PATH = ARTIFACTS_DIR / "backend.json"
_writable_data_dir = Path("/app/data")
_default_mock_key_dir = _writable_data_dir if _writable_data_dir.is_dir() else ARTIFACTS_DIR
MOCK_KEY_DIR = Path(os.getenv("SAKSHI_SIDECAR_MOCK_KEY_DIR", str(_default_mock_key_dir)))
MOCK_PRIVATE_KEY_PATH = MOCK_KEY_DIR / "mock_attestation_private.pem"
MOCK_PUBLIC_KEY_PATH = MOCK_KEY_DIR / "mock_attestation_public.pem"


def validate_features(features: dict[str, float]) -> list[float]:
    if not isinstance(features, dict):
        raise ValueError("features must be an object keyed by shared.types.FEATURE_ORDER")
    missing = [name for name in FEATURE_ORDER if name not in features]
    extra = [name for name in features if name not in FEATURE_ORDER]
    if missing or extra:
        raise ValueError(f"feature schema mismatch; missing={missing}, extra={extra}")
    vector: list[float] = []
    for name in FEATURE_ORDER:
        value = features[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"feature {name!r} must be numeric")
        numeric = float(value)
        if not (float("-inf") < numeric < float("inf")):
            raise ValueError(f"feature {name!r} must be finite")
        vector.append(numeric)
    return vector


def _canonical_public_statement(*, decision_id: str, policy_id: str, policy_hash: str,
                                model_commitment: str, input_commitment: str, decision: int,
                                threshold: float, epoch: int, feature_vector: list[float]) -> bytes:
    body = {
        "format": "sakshi-mock-attestation-v1",
        "decision_id": decision_id,
        "policy_id": policy_id,
        "policy_hash": policy_hash,
        "C": model_commitment,
        "X": input_commitment,
        "decision": decision,
        "threshold": float(threshold),
        "epoch": epoch,
        "feature_vector_sha256": hashlib.sha256(json.dumps(feature_vector, separators=(",", ":")).encode()).hexdigest(),
        "fixed_point_scale": FIXED_POINT_SCALE,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _load_or_create_mock_signing_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    MOCK_KEY_DIR.mkdir(parents=True, exist_ok=True)
    if MOCK_PRIVATE_KEY_PATH.exists() and MOCK_PUBLIC_KEY_PATH.exists():
        private = serialization.load_pem_private_key(MOCK_PRIVATE_KEY_PATH.read_bytes(), password=None)
        public = serialization.load_pem_public_key(MOCK_PUBLIC_KEY_PATH.read_bytes())
        return private, public
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    MOCK_PRIVATE_KEY_PATH.write_bytes(private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    MOCK_PUBLIC_KEY_PATH.write_bytes(public.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    try:
        MOCK_PRIVATE_KEY_PATH.chmod(0o600)
    except OSError:
        pass
    return private, public


def _mock_proof(statement: bytes) -> bytes:
    private, public = _load_or_create_mock_signing_key()
    from cryptography.hazmat.primitives import serialization
    signature = private.sign(statement)
    public_pem = public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    envelope = {
        "format": "SAKSHI_MOCK_ATTESTATION_NOT_ZK_V1",
        "statement_b64": base64.b64encode(statement).decode("ascii"),
        "signature_b64": base64.b64encode(signature).decode("ascii"),
        "verification_key_pem": public_pem.decode("ascii"),
        "warning": "This is a development signature, not a zero-knowledge proof of model execution."
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")


def generate_zk_proof(
    decision_id: str,
    policy_id: str,
    features: dict[str, float],
    decision: int,
    policy_hash: str,
    model_commitment: str,
    threshold: float = 0.200,
    allow_mock: bool | None = None,
) -> ProofPayload:
    """Return shared ProofPayload; native EZKL first, explicit mock fallback second."""
    if decision not in (0, 1):
        raise ValueError("decision must be 0 or 1")
    if not decision_id or not policy_id or not policy_hash or not model_commitment:
        raise ValueError("decision_id, policy_id, policy_hash, and model_commitment are required")
    if not (float("-inf") < float(threshold) < float("inf")):
        raise ValueError("threshold must be finite")

    vector = validate_features(features)
    input_commitment = compute_input_hash(features)
    epoch = today_epoch()
    statement = _canonical_public_statement(
        decision_id=decision_id, policy_id=policy_id, policy_hash=policy_hash,
        model_commitment=model_commitment, input_commitment=input_commitment,
        decision=decision, threshold=threshold, epoch=epoch, feature_vector=vector,
    )
    backend = "mock-not-zk"
    proof_bytes: bytes

    if allow_mock is None:
        allow_mock = os.getenv("SAKSHI_ALLOW_MOCK_PROOFS", "true").strip().lower() in {"1", "true", "yes"}
    try:
        import ezkl  # type: ignore[import-not-found]
        if not all(path.is_file() for path in (COMPILED_PATH, PK_PATH, SETTINGS_PATH, BACKEND_PATH)):
            raise FileNotFoundError("EZKL compiled circuit/proving key/settings missing; run python -m circuits.compile")
        backend_metadata = json.loads(BACKEND_PATH.read_text(encoding="utf-8"))
        # The current ONNX-only circuit proves inference, not the full contract statement.
        # Never label that as contract-conformance proof until the metadata is in-circuit.
        if backend_metadata.get("backend") != "ezkl" or backend_metadata.get("statement_binding") != "full-policy-binding":
            raise RuntimeError("compiled circuit does not constrain policy hash, C, X, decision, and threshold as public inputs")
        # EZKL witness input order is deliberately sourced from shared.types.FEATURE_ORDER.
        witness_input = {"input_data": [vector]}
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        # Temporary inputs/witnesses may contain personal features; delete them on every exit.
        with tempfile.TemporaryDirectory(prefix="sakshi-prove-", dir=str(ARTIFACTS_DIR)) as temp_dir:
            temp_root = Path(temp_dir)
            witness_input_path = temp_root / "input.json"
            witness_path = temp_root / "witness.json"
            proof_path = temp_root / "proof.json"
            witness_input_path.write_text(json.dumps(witness_input), encoding="utf-8")
            ezkl.gen_witness(str(witness_input_path), str(COMPILED_PATH), str(witness_path))
            started = time.perf_counter()
            ezkl.prove(str(witness_path), str(COMPILED_PATH), str(PK_PATH), str(proof_path), "single")
            proof_bytes = proof_path.read_bytes()
        backend = "ezkl"
    except Exception as exc:
        if not allow_mock:
            raise RuntimeError(f"EZKL proving failed and mock fallback is disabled: {exc}") from exc
        proof_bytes = _mock_proof(statement)
        backend = "mock-not-zk"

    # Keep ProofPayload contract stable; backend can be identified by decoding proof bytes.
    proof_b64 = base64.b64encode(proof_bytes).decode("ascii")
    public_inputs = PublicInputs(
        policy_hash=policy_hash, C=model_commitment, X=input_commitment,
        decision=decision, threshold=float(threshold), epoch=epoch,
    )
    return ProofPayload(decision_id=decision_id, policy_id=policy_id, proof=proof_b64, public_inputs=public_inputs)


def _safe_id(value: str) -> str:
    cleaned = "".join(c for c in value if c.isalnum() or c in "-_")[:80]
    if not cleaned:
        raise ValueError("decision_id contains no safe filename characters")
    return cleaned
