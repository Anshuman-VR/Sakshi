"""Environment-driven sidecar settings; safe development defaults are explicit."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class SidecarConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAKSHI_SIDECAR_", extra="ignore")

    lender_node_url: str = "http://lender-node:8000"
    sidecar_api_key: str = "sakshi-dev-key"
    policy_id: str = "pol_nbfc42_lspX_personal_v1"
    policy_path: str = "policy/example_policy.json"
    db_path: str = "sidecar.db"
    port: int = 8001
    num_workers: int = 2
    proof_sla_minutes: int = 10
    request_timeout_seconds: float = 10.0
    retry_base_seconds: float = 1.0
    retry_max_seconds: float = 300.0
    allow_mock_proofs: bool = True
    model_commitment: str = ""
    policy_hash: str = ""


config = SidecarConfig()
