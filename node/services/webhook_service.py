"""Signed outbound webhook delivery with bounded retries."""
import asyncio, hashlib, hmac, json
from datetime import datetime, timezone
import httpx
from node.config import config


class WebhookService:
    async def send(self, decision, event: str, retries: int = 3) -> bool:
        url = config.mock_lms_webhook_url
        secret = config.webhook_secret.get_secret_value()
        if not url:
            return False
        if not secret:
            return False
        body = json.dumps({"event": event, "decision_id": decision.decision_id,
                           "status": decision.status,
                           "ts": datetime.now(timezone.utc).isoformat()},
                          sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        for attempt in range(max(1, retries)):
            try:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                    response = await client.post(url, content=body, headers={
                        "Content-Type": "application/json", "X-Sakshi-Signature": signature})
                if 200 <= response.status_code < 300:
                    return True
                if response.status_code < 500:
                    return False
            except httpx.RequestError:
                pass
            if attempt + 1 < retries:
                await asyncio.sleep(min(2 ** attempt, 4))
        return False


webhook_service = WebhookService()
