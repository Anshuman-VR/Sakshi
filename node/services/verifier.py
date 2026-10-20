"""Ordered V1-V9 verification pipeline. Any uncertainty fails closed."""
import base64
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from shared.types import ProofPayload, VerificationResult
from node.config import config
from node.models import Decision, Policy, ProofRecord, RegisteredModel, InputBinding
from node.services.crypto import decode_b64, canonical_json
from node.services.proof_binding import load_binding_artifacts, proof_instances_match

VERIFICATION_STEPS = [
    "V1_POLICY_EXISTS", "V2_MODEL_APPROVED", "V3_POLICY_HASH_MATCH",
    "V4_THRESHOLD_MATCH", "V5_WINDOW_VALID", "V6_UNIQUENESS",
    "V7_DECISION_MATCH", "V8_ZK_VERIFY", "V9_HARD_RULES",
]


def proof_digest(payload: ProofPayload) -> tuple[bytes, str, bool]:
    try:
        proof_bytes = decode_b64(payload.proof)
        return proof_bytes, hashlib.sha256(proof_bytes).hexdigest(), True
    except ValueError:
        raw = payload.proof.encode("utf-8")
        return b"", hashlib.sha256(raw).hexdigest(), False


def _failed(payload: ProofPayload, proof_hash: str, step: str, reason: str,
            verification_id: str | None = None) -> VerificationResult:
    return VerificationResult(verification_id=verification_id or f"v_{proof_hash[:24]}",
                              decision_id=payload.decision_id, status="FAILED",
                              reason=reason, failed_at_step=step)


def _utc_naive(value: datetime) -> datetime:
    return value.replace(tzinfo=None) if value.tzinfo else value


def _real_ezkl_verify(proof_bytes: bytes, vk_text: str, settings_path: str,
                      compiled_circuit_path: str, circuit_hash: str,
                      public_inputs: dict, fixed_point_scale: int,
                      hard_rules: list) -> bool:
    """Verify EZKL proof only after binding claims to actual public instances.

    The current Dev 1 sample circuit does not expose the required Sakshi
    instances. In that case this returns False by design (fail closed).
    """
    artifacts = load_binding_artifacts(settings_path, compiled_circuit_path, circuit_hash,
        config.ezkl_settings_sha256, config.proof_binding_manifest_path,
        config.proof_binding_manifest_sha256)
    if artifacts is None:
        return False
    settings, manifest = artifacts["settings"], artifacts["manifest"]
    try:
        import ezkl  # lazy import; missing dependency can never become a pass
        vk_bytes = decode_b64(vk_text)
        proof_document = json.loads(proof_bytes.decode("utf-8"))
        json.loads(vk_bytes.decode("utf-8"))
        if not isinstance(proof_document, dict):
            return False
        if not proof_instances_match(proof_document, manifest, public_inputs, fixed_point_scale):
            return False
        # The manifest is a separate, deployment-pinned file so native EZKL
        # settings remain byte-for-byte identical to the prover's settings.
        if manifest.get("sakshi_policy_hash") != public_inputs.get("policy_hash"):
            return False
        if canonical_json(manifest.get("sakshi_hard_rules", [])) != canonical_json(hard_rules or []):
            return False
        with tempfile.TemporaryDirectory(prefix="sakshi-verify-") as temp_dir:
            proof_path = os.path.join(temp_dir, "proof.json")
            vk_path = os.path.join(temp_dir, "vk.key")
            with open(proof_path, "wb") as f:
                f.write(proof_bytes)
            with open(vk_path, "wb") as f:
                f.write(vk_bytes)
            result = ezkl.verify(proof_path, settings_path, vk_path)
            return result is True
    except Exception:
        # Native verifier errors are an invalid proof, not a 500 or fail-open.
        return False


def _check_hard_rules(rules: list, public_inputs: dict) -> bool:
    """Evaluate rules only when their operands are actually available and public.

    Public rules are evaluated directly. Private-feature rules are enforced by
    the exact registered circuit; real verification additionally requires the
    pinned settings to declare the same rule list. A missing public value is
    not itself evidence of a violation.
    """
    ops = {"eq": lambda a, b: a == b, "neq": lambda a, b: a != b,
           "gte": lambda a, b: a >= b, "lte": lambda a, b: a <= b,
           "gt": lambda a, b: a > b, "lt": lambda a, b: a < b}
    for rule in rules or []:
        if not isinstance(rule, dict):
            return False
        field = rule.get("field", rule.get("feature"))
        op = rule.get("op")
        target = rule.get("value")
        if op not in ops or target is None:
            return False
        if field not in public_inputs:
            # This feature is a private witness. The verified circuit and its
            # deployment-pinned settings must enforce this exact rule list.
            continue
        actual = public_inputs[field]
        if isinstance(actual, bool) or isinstance(target, bool):
            if op not in {"eq", "neq"}:
                return False
        if isinstance(actual, (int, float)) and not isinstance(actual, bool) and not math.isfinite(float(actual)):
            return False
        try:
            if not ops[op](actual, target):
                return False
        except (TypeError, ValueError):
            return False
    return True


class VerifierEngine:
    @staticmethod
    def run_pipeline(session: Session, payload: ProofPayload,
                     verification_id: str | None = None) -> VerificationResult:
        proof_bytes, proof_hash, encoding_valid = proof_digest(payload)
        verification_id = verification_id or f"v_{proof_hash[:24]}"
        pub = payload.public_inputs
        pub_dict = pub.model_dump(mode="json")
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # V1: Policy exists and is within its contractual validity window.
        policy = session.get(Policy, payload.policy_id)
        if policy is None:
            return _failed(payload, proof_hash, "V1_POLICY_EXISTS", "V1_POLICY_NOT_FOUND", verification_id)
        if policy.status == "REVOKED":
            return _failed(payload, proof_hash, "V1_POLICY_EXISTS", "POLICY_REVOKED", verification_id)
        if policy.status == "EXPIRED" or now < _utc_naive(policy.valid_from) or now > _utc_naive(policy.valid_to):
            return _failed(payload, proof_hash, "V1_POLICY_EXISTS", "POLICY_EXPIRED", verification_id)
        if policy.status != "ACTIVE":
            return _failed(payload, proof_hash, "V1_POLICY_EXISTS", "V1_POLICY_NOT_FOUND", verification_id)

        # V2: commitment must resolve to an approved, non-revoked registered model.
        model = session.execute(select(RegisteredModel).where(RegisteredModel.commitment == pub.C)).scalar_one_or_none()
        if (model is None or model.status != "APPROVED" or model.revoked_at is not None
                or model.commitment != policy.model_commitment or model.circuit_hash != policy.circuit_hash
                or model.feature_schema_hash != policy.feature_schema_hash):
            return _failed(payload, proof_hash, "V2_MODEL_APPROVED", "MODEL_MISMATCH", verification_id)

        # V3: policy identity and canonical hash.
        if pub.policy_hash != policy.policy_hash:
            return _failed(payload, proof_hash, "V3_POLICY_HASH_MATCH", "POLICY_HASH_MISMATCH", verification_id)

        # V4: exact decimal semantics; no epsilon that could admit threshold creep.
        try:
            if not math.isfinite(float(pub.threshold)) or float(pub.threshold) != float(policy.decision_threshold):
                return _failed(payload, proof_hash, "V4_THRESHOLD_MATCH", "THRESHOLD_MISMATCH", verification_id)
        except (TypeError, ValueError):
            return _failed(payload, proof_hash, "V4_THRESHOLD_MATCH", "THRESHOLD_MISMATCH", verification_id)

        # V5: current UTC date or previous UTC date, with explicit calendar logic.
        try:
            epoch_day = datetime.strptime(str(pub.epoch), "%Y%m%d").date() if len(str(pub.epoch)) == 8 else None
        except ValueError:
            epoch_day = None
        today = datetime.now(timezone.utc).date()
        if epoch_day is None or epoch_day not in {today, today - timedelta(days=1)}:
            return _failed(payload, proof_hash, "V5_WINDOW_VALID", "WINDOW_INVALID", verification_id)

        # V6: globally reject an identical proof already reserved by another
        # verification. The current request's reservation is exempt by ID.
        existing_proof_id = session.execute(select(ProofRecord.id).where(
            ProofRecord.proof_hash == proof_hash, ProofRecord.id != verification_id
        )).scalar_one_or_none()
        if existing_proof_id is not None:
            return _failed(payload, proof_hash, "V6_UNIQUENESS", "REPLAY", verification_id)

        # V7: a proof is only meaningful for the exact notice received by the lender.
        decision = session.get(Decision, payload.decision_id)
        if decision is None or decision.policy_id != payload.policy_id or pub.decision != decision.decision:
            return _failed(payload, proof_hash, "V7_DECISION_MATCH", "DECISION_MISMATCH", verification_id)
        if decision.status != "NOTICE_RECEIVED":
            return _failed(payload, proof_hash, "V7_DECISION_MATCH", "DECISION_MISMATCH", verification_id)
        binding = session.execute(select(InputBinding).where(
            InputBinding.decision_id == decision.decision_id,
            InputBinding.application_id_hash == decision.application_id_hash
        ).order_by(InputBinding.bound_at.desc()).limit(1)).scalar_one_or_none()
        if binding is None or binding.x_prime != pub.X:
            if binding is not None:
                binding.binding_status = "MISMATCH"
            return _failed(payload, proof_hash, "V7_DECISION_MATCH", "BINDING_MISMATCH", verification_id)
        binding.binding_status = "MATCHED"
        if datetime.now(timezone.utc).replace(tzinfo=None) > _utc_naive(decision.sla_deadline):
            return _failed(payload, proof_hash, "V5_WINDOW_VALID", "EXPIRED", verification_id)

        # V8: never accept placeholder bytes. Mock is opt-in and prohibited in prod.
        if not encoding_valid or not proof_bytes:
            return _failed(payload, proof_hash, "V8_ZK_VERIFY", "INVALID_PROOF", verification_id)
        if config.mock_verify:
            if (config.environment.lower() in {"production", "prod"}
                    or (config.environment.lower() != "test" and not config.allow_insecure_mock_verify)):
                return _failed(payload, proof_hash, "V8_ZK_VERIFY", "INVALID_PROOF", verification_id)
            proof_valid = proof_bytes.startswith(b"SAKSHI_TEST_VALID_PROOF:")
        else:
            proof_valid = _real_ezkl_verify(proof_bytes, model.vk, config.ezkl_settings_path,
                config.compiled_circuit_path, model.circuit_hash, pub_dict,
                policy.fixed_point_scale, policy.hard_rules)
        if not proof_valid:
            return _failed(payload, proof_hash, "V8_ZK_VERIFY", "INVALID_PROOF", verification_id)

        # V9: public rules are checked directly. Private feature rules are
        # enforced by the registered circuit and must match the deployment's
        # pinned `sakshi_hard_rules` settings metadata in the real EZKL path.
        if not _check_hard_rules(policy.hard_rules, pub_dict):
            return _failed(payload, proof_hash, "V9_HARD_RULES", "HARD_RULE_VIOLATION", verification_id)

        return VerificationResult(verification_id=verification_id, decision_id=payload.decision_id,
                                  status="VERIFIED", verified_at=now.isoformat())
