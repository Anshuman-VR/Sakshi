"""Read-only webhook configuration status; no arbitrary callback/proxy route."""
from fastapi import APIRouter, Depends
from node.config import config
from node.routes.deps import require_lender

router = APIRouter(tags=["webhooks"])


@router.get("/v1/webhooks/status")
def webhook_status(_auth=Depends(require_lender)):
    return {"configured": bool(config.mock_lms_webhook_url and config.webhook_secret.get_secret_value()),
            "delivery": "signed-hmac-sha256", "retries": 3}
