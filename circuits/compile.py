"""Compile the scorecard to an EZKL/Halo2 circuit.

The native circuit proves private-feature inference for the checked-in ONNX
scorecard and exposes the probability as a public output. Policy hash, salted
SHA-256 commitments, epoch and the decision bit are still validated by the
verifier/application layer; this ONNX circuit alone does not constrain them.
The explicit mock fallback is for interface tests only and is NOT zero knowledge.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CIRCUITS_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = CIRCUITS_DIR / "artifacts"
SETTINGS_TEMPLATE_PATH = CIRCUITS_DIR / "settings.json"
SETTINGS_PATH = ARTIFACTS_DIR / "scorecard.settings.json"
COMPILED_PATH = ARTIFACTS_DIR / "scorecard.compiled"
VK_PATH = ARTIFACTS_DIR / "scorecard.vk"
PK_PATH = ARTIFACTS_DIR / "scorecard.pk"
SRS_PATH = ARTIFACTS_DIR / "scorecard.srs"
BACKEND_PATH = ARTIFACTS_DIR / "backend.json"
MODEL_ONNX_PATH = ROOT / "model" / "models" / "scorecard.onnx"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_mock_artifacts(reason: str) -> str:
    """Create labelled non-ZK artifacts for local development/tests."""
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
        "settings_template_sha256": _sha256_file(SETTINGS_TEMPLATE_PATH) if SETTINGS_TEMPLATE_PATH.exists() else None,
    }
    COMPILED_PATH.write_text(json.dumps(descriptor, sort_keys=True, indent=2), encoding="utf-8")
    VK_PATH.write_text(json.dumps({"backend": "mock-not-zk", "key_id": secrets.token_hex(16)}), encoding="utf-8")
    PK_PATH.write_text(json.dumps({"backend": "mock-not-zk", "warning": "not a proving key"}), encoding="utf-8")
    circuit_hash = _sha256_file(COMPILED_PATH)
    BACKEND_PATH.write_text(json.dumps({
        "backend": "mock-not-zk",
        "circuit_hash": circuit_hash,
        "statement_binding": "none",
        "warning": "Development fallback only; not an EZKL/Halo2 proof.",
    }, indent=2), encoding="utf-8")
    return circuit_hash


def _download_srs(ezkl: Any) -> bool:
    """EZKL 23.x exposes get_srs as an awaitable; run it from this sync CLI."""
    async def _get() -> bool:
        result = ezkl.get_srs(str(SETTINGS_PATH), srs_path=str(SRS_PATH))
        if hasattr(result, "__await__"):
            result = await result
        return bool(result)
    return bool(asyncio.run(_get()))


def compile_circuit(
    model_path: str | os.PathLike[str] | None = None, *, allow_mock: bool | None = None, force_mock: bool = False
) -> str:
    """Compile/setup EZKL and return SHA-256 of the compiled circuit bytes."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    if allow_mock is None:
        allow_mock = os.getenv("SAKSHI_ALLOW_MOCK_PROOFS", "true").strip().lower() in {"1", "true", "yes"}
    model_path = Path(model_path) if model_path else MODEL_ONNX_PATH
    if force_mock:
        if not allow_mock:
            raise ValueError("force_mock=True requires allow_mock=True")
        for path in (COMPILED_PATH, VK_PATH, PK_PATH, SRS_PATH, SETTINGS_PATH):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        circuit_hash = _write_mock_artifacts("force_mock=True requested by a development/test caller")
        return circuit_hash

    try:
        import ezkl  # type: ignore[import-not-found]
        if not model_path.is_file():
            raise FileNotFoundError(f"ONNX model not found: {model_path}")
        if not hasattr(ezkl, "PyRunArgs"):
            raise RuntimeError("EZKL version lacks PyRunArgs; install the pinned EZKL 23.0.5 dependency")

        # The model input is borrower data, so keep it private. The model is a
        # fixed circuit parameter; its verifier key/circuit identity must be
        # registered against the approved model commitment by the policy layer.
        # SAFE checks plus 3 decomposition legs accommodate the INR-valued inputs.
        run_args = ezkl.PyRunArgs()
        run_args.input_visibility = "private"
        run_args.output_visibility = "public"
        run_args.param_visibility = "fixed"
        run_args.check_mode = "safe"
        run_args.input_scale = 10
        run_args.param_scale = 10
        run_args.decomp_legs = 3
        run_args.logrows = 17

        print(f"Compiling ONNX scorecard with EZKL {getattr(ezkl, '__version__', '23.x')}...")
        if not ezkl.gen_settings(str(model_path), str(SETTINGS_PATH), py_run_args=run_args):
            raise RuntimeError("EZKL failed to generate settings")
        if not ezkl.compile_circuit(str(model_path), str(COMPILED_PATH), str(SETTINGS_PATH)):
            raise RuntimeError("EZKL failed to compile the circuit")
        if not _download_srs(ezkl):
            raise RuntimeError("EZKL failed to download/generate the SRS")
        if not ezkl.setup(str(COMPILED_PATH), str(VK_PATH), str(PK_PATH), srs_path=str(SRS_PATH)):
            raise RuntimeError("EZKL setup did not complete")

        circuit_hash = _sha256_file(COMPILED_PATH)
        from model.commit import compute_model_commitment
        model_commitment = compute_model_commitment()
        if not model_commitment.startswith("0x"):
            model_commitment = "0x" + model_commitment
        metadata = {
            "backend": "ezkl",
            "ezkl_version": getattr(ezkl, "__version__", "unknown"),
            "circuit_hash": circuit_hash,
            "model_commitment": model_commitment,
            "model_onnx_sha256": _sha256_file(model_path),
            "settings_sha256": _sha256_file(SETTINGS_PATH),
            "srs_sha256": _sha256_file(SRS_PATH),
            "statement_binding": "model-inference-only",
            "input_visibility": "private",
            "output_visibility": "public-probability",
            "parameter_visibility": "fixed",
            "output_name": "probability",
            "warning": "Proof binds private-input inference to a public probability only. Policy hash, C, X, threshold, decision and epoch need verifier-layer checks; they are not all in this circuit statement.",
        }
        BACKEND_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Native EZKL circuit compiled. SHA-256: {circuit_hash}")
        return circuit_hash
    except Exception as exc:
        if not allow_mock:
            raise RuntimeError(f"EZKL compilation failed and mock fallback is disabled: {exc}") from exc
        # Remove partial/stale native artifacts so they cannot be mistaken for a
        # successfully compiled circuit after an interrupted or failed setup.
        for path in (COMPILED_PATH, VK_PATH, PK_PATH, SRS_PATH, SETTINGS_PATH):
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
