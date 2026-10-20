"""Sakshi Lender Node API: policy enforcement, ZK verification, ledger and gate."""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy import text
from node.config import config
from node.database import SessionLocal, init_db
from node.routes.models_route import router as models_router
from node.routes.policies_route import router as policies_router
from node.routes.decisions_route import router as decisions_router
from node.routes.proofs_route import router as proofs_router
from node.routes.gate_route import router as gate_router
from node.routes.ledger_route import router as ledger_router
from node.routes.dashboard_route import router as dashboard_router
from node.routes.bindings_route import router as bindings_router
from node.routes.webhooks_route import router as webhooks_router
from node.routes.demo_route import router as demo_router
from node.services.ledger import LedgerService
from node.services.sla_monitor import sla_monitor_loop
from node.services.metrics import render_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("sakshi.node")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.auto_create_schema:
        init_db()
    task = asyncio.create_task(sla_monitor_loop(config.sla_poll_seconds), name="sakshi-sla-monitor")
    app.state.sla_task = task
    logger.info("Lender Node started; mock_verify=%s environment=%s", config.mock_verify, config.environment)
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Sakshi Lender Node & Disbursal Gate", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins,
                   allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Sakshi-Key", "X-Lender-Key"])

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

for router in (models_router, policies_router, decisions_router, proofs_router, gate_router,
               ledger_router, dashboard_router, bindings_router, webhooks_router, demo_router):
    app.include_router(router)


# Mount static assets and SPA fallback for React frontend
dist_path = Path("dashboard/dist")
if not dist_path.is_dir():
    dist_path = Path("/app/dashboard/dist")

if dist_path.is_dir():
    assets_dir = dist_path / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(request: Request, full_path: str):
        # Allow API routes, health, metrics, and docs to pass through
        if full_path.startswith(("v1/", "healthz", "metrics", "docs", "openapi.json")):
            return JSONResponse(status_code=404, content={"detail": "NOT_FOUND"})
        file_path = dist_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        index_file = dist_path / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return JSONResponse(status_code=404, content={"detail": "NOT_FOUND"})


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error method=%s path=%s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "INTERNAL_ERROR"})


@app.get("/healthz")
def healthz():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            ledger_seq = LedgerService.current_sequence(db)
        return {"status": "ok", "service": "sakshi-lender-node", "db": "ok", "ledger_seq": ledger_seq}
    except Exception:
        logger.exception("Health check failed")
        return JSONResponse(status_code=503, content={"status": "unavailable", "db": "error"})


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    try:
        with SessionLocal() as db:
            return PlainTextResponse(render_metrics(db), media_type="text/plain; version=0.0.4; charset=utf-8")
    except Exception:
        logger.exception("Metrics collection failed")
        return PlainTextResponse("# metrics unavailable\n", status_code=503)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("node.main:app", host="0.0.0.0", port=config.port, reload=False)
