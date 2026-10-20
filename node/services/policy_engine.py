"""Policy parsing, validation and trusted-key signature checks."""
from datetime import datetime, timezone
from shared.types import ModelRegistration, PolicyDocument
from node.config import config
from node.models import Policy, RegisteredModel
from node.services.crypto import (model_registration_signing_payload, policy_signing_payload,
                                  verify_ed25519)


def _trusted_key(configured: str, supplied: str) -> bool:
    # In production a public key must be pinned by deployment configuration.
    if configured:
        return configured.lower() == supplied.lower()
    return config.environment.lower() not in {"production", "prod"}


def validate_model_registration(payload: ModelRegistration) -> bool:
    if not _trusted_key(config.lsp_pubkey, payload.lsp_pubkey):
        return False
    try:
        return verify_ed25519(payload.lsp_pubkey, payload.lsp_sig,
                              model_registration_signing_payload(payload.model_dump(mode="json")))
    except Exception:
        return False


def validate_policy_signatures(payload: PolicyDocument) -> bool:
    if not _trusted_key(config.lsp_pubkey, payload.lsp_pubkey):
        return False
    if not _trusted_key(config.lender_pubkey, payload.lender_pubkey):
        return False
    message = policy_signing_payload(payload.model_dump(mode="json"))
    return (verify_ed25519(payload.lsp_pubkey, payload.lsp_sig, message)
            and verify_ed25519(payload.lender_pubkey, payload.lender_sig, message))


def parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Datetime must include timezone information")
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def policy_to_document(policy: Policy) -> dict:
    return dict(policy.canonical_document, lsp_sig=policy.lsp_sig, lender_sig=policy.lender_sig)


def model_public(model: RegisteredModel) -> dict:
    return {"id": model.id, "commitment": model.commitment, "circuit_hash": model.circuit_hash,
            "feature_schema_hash": model.feature_schema_hash, "parity_report": model.parity_report,
            "status": model.status, "registered_at": model.registered_at.isoformat(),
            "approved_at": model.approved_at.isoformat() if model.approved_at else None,
            "revoked_at": model.revoked_at.isoformat() if model.revoked_at else None}
