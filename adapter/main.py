"""Lender-network-only input binding API on port 8003."""
import os, re, logging
import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from adapter.binder import bind

logger = logging.getLogger("sakshi.adapter")
NODE_URL = os.getenv("SAKSHI_ADAPTER_NODE_URL", "http://127.0.0.1:8000")
LENDER_KEY = os.getenv("SAKSHI_NODE_LENDER_ADMIN_KEY", "")
app = FastAPI(title="Sakshi Input Binding Adapter", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[], allow_credentials=False,
                   allow_methods=["POST", "OPTIONS"], allow_headers=["Content-Type", "X-Lender-Key"])


class BindRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_id_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")
    features: dict[str, float]
    decision_id: str | None = None


@app.post("/v1/bind")
async def bind_inputs(payload: BindRequest, x_lender_key: str | None = Header(default=None, alias="X-Lender-Key")):
    # Adapter auth and downstream node auth are both required; never forward an
    # arbitrary user-supplied URL or accept raw features from an unauthenticated caller.
    import hmac
    if not LENDER_KEY or not x_lender_key or not hmac.compare_digest(LENDER_KEY, x_lender_key):
        raise HTTPException(401, "UNAUTHORIZED")
    try:
        return await bind(payload.application_id_hash, payload.features, NODE_URL, LENDER_KEY, payload.decision_id)
    except ValueError as exc:
        raise HTTPException(422, "INVALID_FEATURES")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(exc.response.status_code, "BINDING_REQUEST_FAILED")
    except Exception:
        logger.exception("Input binding request failed")
        raise HTTPException(502, "BINDING_SERVICE_UNAVAILABLE")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "sakshi-input-binding-adapter"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("adapter.main:app", host="0.0.0.0", port=8003, reload=False)
