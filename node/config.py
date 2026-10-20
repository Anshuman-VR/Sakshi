"""Validated configuration for the Sakshi Lender Node.

Secrets deliberately have no production-safe implicit default. Supply them via
SAKSHI_NODE_* environment variables or a secret manager.
"""
from functools import lru_cache
from pathlib import Path
from importlib.util import find_spec
import hashlib
import json
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NodeConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAKSHI_NODE_", extra="ignore")

    database_url: str = "sqlite:///./data/sakshi.db"
    sidecar_api_key: SecretStr = SecretStr("")
    lender_admin_key: SecretStr = SecretStr("")
    lender_pubkey: str = ""
    lsp_pubkey: str = ""
    webhook_secret: SecretStr = SecretStr("")
    mock_lms_webhook_url: str = ""
    ezkl_settings_path: str = ""
    ezkl_settings_sha256: str = ""
    compiled_circuit_path: str = ""
    proof_binding_manifest_path: str = ""
    proof_binding_manifest_sha256: str = ""
    mock_verify: bool = False
    allow_insecure_mock_verify: bool = False
    environment: str = "production"
    port: int = Field(default=8000, ge=1, le=65535)
    sla_poll_seconds: float = Field(default=5.0, gt=0, le=300)
    proof_max_bytes: int = Field(default=5_000_000, ge=1024)
    cors_origins: list[str] = ["*"]
    auto_create_schema: bool = True

    @field_validator("database_url")
    @classmethod
    def normalize_sync_database_url(cls, value: str) -> str:
        # The service intentionally uses SQLAlchemy's synchronous session API;
        # accept the historical aiosqlite URL from compose without silently
        # selecting an async driver for a sync engine.
        if value.startswith("sqlite+aiosqlite://"):
            return value.replace("sqlite+aiosqlite://", "sqlite://", 1)
        if value.startswith("postgresql+asyncpg://"):
            return value.replace("postgresql+asyncpg://", "postgresql://", 1)
        return value

    @model_validator(mode="after")
    def validate_security_settings(self):
        if self.mock_verify and self.environment.lower() in {"production", "prod"}:
            raise ValueError("MOCK_VERIFY is forbidden in production")
        if self.mock_verify and not self.allow_insecure_mock_verify:
            raise ValueError("MOCK_VERIFY requires explicit SAKSHI_NODE_ALLOW_INSECURE_MOCK_VERIFY=true")
        if self.environment.lower() in {"production", "prod"}:
            if not self.sidecar_api_key.get_secret_value() or not self.lender_admin_key.get_secret_value():
                raise ValueError("Sidecar and lender admin API keys are required in production")
            if not self.lender_pubkey or not self.lsp_pubkey:
                raise ValueError("Pinned lender and LSP Ed25519 public keys are required in production")
            if not self.ezkl_settings_path or not Path(self.ezkl_settings_path).is_file():
                raise ValueError("A mounted EZKL settings file is required in production")
            settings_hash = self.ezkl_settings_sha256.removeprefix("0x")
            if len(settings_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in settings_hash):
                raise ValueError("A valid pinned EZKL settings SHA-256 is required in production")
            if hashlib.sha256(Path(self.ezkl_settings_path).read_bytes()).hexdigest().lower() != settings_hash.lower():
                raise ValueError("Mounted EZKL settings do not match the pinned SHA-256")
            if not self.compiled_circuit_path or not Path(self.compiled_circuit_path).is_file():
                raise ValueError("A mounted compiled circuit is required in production")
            if not self.proof_binding_manifest_path or not Path(self.proof_binding_manifest_path).is_file():
                raise ValueError("A pinned Sakshi proof-binding manifest is required in production")
            manifest_hash = self.proof_binding_manifest_sha256.removeprefix("0x")
            if len(manifest_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in manifest_hash):
                raise ValueError("A valid proof-binding manifest SHA-256 is required in production")
            if hashlib.sha256(Path(self.proof_binding_manifest_path).read_bytes()).hexdigest().lower() != manifest_hash.lower():
                raise ValueError("Mounted proof-binding manifest does not match the pinned SHA-256")
            try:
                manifest = json.loads(Path(self.proof_binding_manifest_path).read_text(encoding="utf-8"))
                if not isinstance(manifest, dict):
                    raise ValueError
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("Proof-binding manifest must be valid JSON") from exc
            if find_spec("ezkl") is None:
                raise ValueError("The EZKL verifier dependency is required in production")
            if self.mock_lms_webhook_url and not self.webhook_secret.get_secret_value():
                raise ValueError("Webhook secret is required when webhook delivery is configured")
            if self.mock_verify:
                raise ValueError("Mock proof verification is forbidden in production")
        return self


@lru_cache(maxsize=1)
def get_config() -> NodeConfig:
    return NodeConfig()


config = get_config()
