"""Shared authentication dependencies. No credential is accepted by default."""
import hmac
from fastapi import Header, HTTPException, status
from node.config import config


def require_sidecar(x_sakshi_key: str | None = Header(default=None, alias="X-Sakshi-Key")) -> None:
    expected = config.sidecar_api_key.get_secret_value()
    if not expected or not x_sakshi_key or not hmac.compare_digest(expected, x_sakshi_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")


def require_lender(x_lender_key: str | None = Header(default=None, alias="X-Lender-Key")) -> None:
    expected = config.lender_admin_key.get_secret_value()
    if not expected or not x_lender_key or not hmac.compare_digest(expected, x_lender_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
