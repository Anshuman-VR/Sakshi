"""Compile the scorecard circuit with EZKL, with an explicit development fallback.

The fallback artifacts are NOT a zero-knowledge proof system. They enable local
workflow testing only and are marked as mock artifacts so production code can
fail closed instead of confusing them with EZKL/Halo2 proofs.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CIRCUITS_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = CIRCUITS_DIR / "artifacts"
SETTINGS_PATH = CIRCUITS_DIR / "settings.json"
COMPILED_PATH = ARTIFACTS_DIR / "scorecard.compiled"
VK_PATH = ARTIFACTS_DIR / "scorecard.vk"
PK_PATH = ARTIFACTS_DIR / "scorecard.pk"
BACKEND_PATH = ARTIFACTS_DIR / "backend.json"
MODEL_ONNX_PATH = ROOT / "model" / "models" / "scorecard.onnx"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_mock_artifacts(reason: str) -> str:
    """Create clearly labelled non-ZK artifacts for development/test execution."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from shared.types import FEATURE_ORDER, FIXED_POINT_SCALE
        feature_order = list(FEATURE_ORDER)
    except Exception:
        feature_order, FIXED_POINT_SCALE = [], 1024
    descriptor = {
        "format": "sakshi-mock-circuit-v1",
        "backend": "mock-not-zk",
        "reason": reason[:500],
        "feature_order": feature_order,
        "fixed_point_scale": FIXED_POINT_SCALE,
        "settings_sha256": _sha256_file(SETTINGS_PATH) if SETTINGS_PATH.exists() else None,
    }
    COMPILED_PATH.write_text(json.dumps(descriptor, sort_keys=True, indent=2), encoding="utf-8")
    # These are markers, not cryptographic proving/verification keys.
    VK_PATH.write_text(json.dumps({"backend": "mock-not-zk", "key_id": secrets.token_hex(16)}), encoding="utf-8")
    PK_PATH.write_text(json.dumps({"backend": "mock-not-zk", "warning": "not a proving key"}), encoding="utf-8")
    circuit_hash = _sha256_file(COMPILED_PATH)
    BACKEND_PATH.write_text(json.dumps({
        "backend": "mock-not-zk", "circuit_hash": circuit_hash,
        "warning": "Development fallback only; never claim this is a Halo2/ZK proof."
    }, indent=2), encoding="utf-8")
    return circuit_hash


def compile_circuit(model_path: str | os.PathLike[str] | None = None, *, allow_mock: bool | None = None) -> str:
    """Compile/setup EZKL. Return SHA-256 of compiled circuit bytes.

    When EZKL or the ONNX model is unavailable, fall back only if `allow_mock`
    is true (defaults to SAKSHI_ALLOW_MOCK_PROOFS=true for hackathon development).
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    if allow_mock is None:
        allow_mock = os.getenv("SAKSHI_ALLOW_MOCK_PROOFS", "true").strip().lower() in {"1", "true", "yes"}
    model_path = Path(model_path) if model_path else MODEL_ONNX_PATH
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text(json.dumps({"run_args": {"scale": 10, "bits": 16, "logrows": 12}}, indent=2), encoding="utf-8")

    try:
        import ezkl  # type: ignore[import-not-found]
        if not model_path.is_file():
            raise FileNotFoundError(f"ONNX model not found: {model_path}")
        print("Compiling with native EZKL; this may take several minutes...")
        # EZKL versions expose these functions as synchronous calls.
        ezkl.gen_settings(str(model_path), str(SETTINGS_PATH))
        calibration_path = ROOT / "model" / "data" / "calibration.json"
        if calibration_path.is_file() and hasattr(ezkl, "calibrate_settings"):
            ezkl.calibrate_settings(str(calibration_path), str(model_path), str(SETTINGS_PATH), target="resources")
        ezkl.compile_circuit(str(model_path), str(COMPILED_PATH), str(SETTINGS_PATH))
        ezkl.setup(str(COMPILED_PATH), str(VK_PATH), str(PK_PATH))
        circuit_hash = _sha256_file(COMPILED_PATH)
        BACKEND_PATH.write_text(json.dumps({"backend": "ezkl", "circuit_hash": circuit_hash, "statement_binding": "model-inference-only", "warning": "Policy hash, C, X, decision, and threshold are not yet enforced as in-circuit public inputs."}, indent=2), encoding="utf-8")
        print(f"EZKL circuit compiled. SHA-256: {circuit_hash}")
        return circuit_hash
    except Exception as exc:
        if not allow_mock:
            raise RuntimeError(f"EZKL compilation failed and mock fallback is disabled: {exc}") from exc
        # Remove partial outputs so a failed native compile cannot be mistaken for success.
        for path in (COMPILED_PATH, VK_PATH, PK_PATH):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        circuit_hash = _write_mock_artifacts(f"{type(exc).__name__}: {exc}")
        print("WARNING: EZKL unavailable/failed; generated MOCK-NOT-ZK artifacts for development only.")
        print(f"Mock circuit descriptor hash: {circuit_hash}")
        return circuit_hash


if __name__ == "__main__":
    compile_circuit()
