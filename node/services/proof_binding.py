"""Bind API-supplied Sakshi claims to the actual EZKL proof instances.

The EZKL proof's instances are authoritative. `ProofPayload.public_inputs` is
untrusted request metadata and must not be accepted merely because EZKL verifies
some proof. The settings artifact must explicitly declare the instance indices
used by the Sakshi circuit. Missing/ambiguous metadata fails closed.

Expected settings JSON extension:
{
  "sakshi_public_input_binding": {
    "version": 1,
    "threshold_scale": 1024,
    "indices": {
      "policy_hash_hi": 0, "policy_hash_lo": 1,
      "C_hi": 2, "C_lo": 3, "X_hi": 4, "X_lo": 5,
      "decision": 6, "threshold_scaled": 7, "epoch": 8
    }
  }
}
Hash values are 32-byte hex split into two unsigned 128-bit big-endian chunks,
serialized as decimal field elements. The circuit must expose these exact values
as public instances. This extension is not present in the current Dev 1 sample
circuit; real-proof verification remains disabled until it is implemented there.
"""
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

_REQUIRED = ("policy_hash_hi", "policy_hash_lo", "C_hi", "C_lo", "X_hi", "X_lo",
             "decision", "threshold_scaled", "epoch")
_HEX_64 = re.compile(r"^[0-9a-fA-F]{64}$")


def _hash_chunks(value: str) -> tuple[str, str] | None:
    value = value.removeprefix("0x").removeprefix("0X")
    if not _HEX_64.fullmatch(value):
        return None
    return str(int(value[:32], 16)), str(int(value[32:], 16))


def _instance_text(value) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        raw = value.strip()
        try:
            return str(int(raw, 16)) if raw.lower().startswith("0x") else str(int(raw, 10))
        except ValueError:
            return None
    return None


def proof_instances_match(proof_document: dict, settings_document: dict, public_inputs: dict,
                          fixed_point_scale: int) -> bool:
    """Compare actual EZKL public instances with the exact claims in the API request."""
    binding = settings_document.get("sakshi_public_input_binding")
    if not isinstance(binding, dict) or binding.get("version") != 1:
        return False
    indices = binding.get("indices")
    if not isinstance(indices, dict) or set(indices) != set(_REQUIRED):
        return False
    try:
        normalized_indices = {name: int(indices[name]) for name in _REQUIRED}
    except (TypeError, ValueError):
        return False
    if any(i < 0 for i in normalized_indices.values()) or len(set(normalized_indices.values())) != len(_REQUIRED):
        return False
    instances = proof_document.get("instances")
    if not isinstance(instances, list):
        return False
    flattened = []
    for group in instances:
        if isinstance(group, list):
            flattened.extend(group)
        else:
            flattened.append(group)
    if max(normalized_indices.values()) >= len(flattened):
        return False
    policy_chunks = _hash_chunks(str(public_inputs.get("policy_hash", "")))
    c_chunks = _hash_chunks(str(public_inputs.get("C", "")))
    x_chunks = _hash_chunks(str(public_inputs.get("X", "")))
    if not policy_chunks or not c_chunks or not x_chunks or fixed_point_scale <= 0:
        return False
    try:
        scaled_threshold = (Decimal(str(public_inputs["threshold"])) * Decimal(fixed_point_scale)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP)
        expected = {
            "policy_hash_hi": policy_chunks[0], "policy_hash_lo": policy_chunks[1],
            "C_hi": c_chunks[0], "C_lo": c_chunks[1],
            "X_hi": x_chunks[0], "X_lo": x_chunks[1],
            "decision": str(int(public_inputs["decision"])),
            "threshold_scaled": str(int(scaled_threshold)),
            "epoch": str(int(public_inputs["epoch"])),
        }
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return False
    for name, expected_value in expected.items():
        actual = _instance_text(flattened[normalized_indices[name]])
        if actual is None or actual != expected_value:
            return False
    configured_scale = binding.get("threshold_scale", fixed_point_scale)
    try:
        if int(configured_scale) != fixed_point_scale:
            return False
    except (TypeError, ValueError):
        return False
    return True


def load_binding_artifacts(settings_path: str, compiled_circuit_path: str, expected_circuit_hash: str,
                           expected_settings_hash: str, manifest_path: str,
                           expected_manifest_hash: str):
    """Load the native EZKL settings unchanged plus a separately pinned manifest."""
    if not all((settings_path, compiled_circuit_path, expected_settings_hash,
                manifest_path, expected_manifest_hash)):
        return None
    settings_file, circuit_file, manifest_file = Path(settings_path), Path(compiled_circuit_path), Path(manifest_path)
    if not settings_file.is_file() or not circuit_file.is_file() or not manifest_file.is_file():
        return None
    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if not isinstance(settings, dict) or not isinstance(manifest, dict):
            return None
        import hashlib
        actual_circuit_hash = hashlib.sha256(circuit_file.read_bytes()).hexdigest()
        actual_settings_hash = hashlib.sha256(settings_file.read_bytes()).hexdigest()
        actual_manifest_hash = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
        if actual_circuit_hash.lower() != expected_circuit_hash.removeprefix("0x").lower():
            return None
        if actual_settings_hash.lower() != expected_settings_hash.removeprefix("0x").lower():
            return None
        if actual_manifest_hash.lower() != expected_manifest_hash.removeprefix("0x").lower():
            return None
        if manifest.get("circuit_hash", "").removeprefix("0x").lower() != actual_circuit_hash.lower():
            return None
        if manifest.get("settings_sha256", "").removeprefix("0x").lower() != actual_settings_hash.lower():
            return None
        return {"settings": settings, "manifest": manifest}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return None
