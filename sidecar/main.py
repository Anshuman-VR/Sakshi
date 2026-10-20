"""FastAPI entry point for the private LSP prover sidecar."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from shared.types import DecisionEvent, JobStatus, FEATURE_ORDER, compute_application_hash
from circuits.prove import validate_features
from sidecar.config import config
from sidecar.database import SessionLocal, init_db
from sidecar.models import ProverJob, OutboxMessage, utcnow
from sidecar.prover_worker import prover_loop, recover_interrupted_jobs

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def create_app(*, start_worker: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        init_db()
        recovered = recover_interrupted_jobs()
        if recovered:
            log.warning("Requeued %s interrupted proving jobs", recovered)
        tasks: list[asyncio.Task] = []
        stop_event = asyncio.Event()
        if start_worker:
            # SQLite claim logic is idempotent; multiple workers are supported.
            for _ in range(max(1, config.num_workers)):
                tasks.append(asyncio.create_task(prover_loop(stop_event)))
        app.state.worker_tasks = tasks
        app.state.stop_event = stop_event
        try:
            yield
        finally:
            stop_event.set()
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title="Sakshi LSP Prover Sidecar", version="1.0.0", lifespan=lifespan)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "service": "sakshi-sidecar", "version": app.version}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics():
        with SessionLocal() as session:
            jobs = session.scalars(select(ProverJob)).all()
            pending_count = len(session.scalars(select(OutboxMessage).where(OutboxMessage.status == "PENDING")).all())
        counts: dict[str, int] = {}
        for job in jobs:
            counts[job.status] = counts.get(job.status, 0) + 1
        lines = ["# HELP sakshi_proofs_total Number of prover jobs by status.", "# TYPE sakshi_proofs_total counter"]
        for status in ("QUEUED", "PROVING", "UPLOADED", "VERIFIED", "FAILED"):
            lines.append(f'sakshi_proofs_total{{status="{status}"}} {counts.get(status, 0)}')
        durations = [job.proving_duration_ms / 1000 for job in jobs if job.proving_duration_ms is not None]
        lines.extend(["# HELP sakshi_proof_duration_seconds Duration of local proof generation.", "# TYPE sakshi_proof_duration_seconds summary",
                      f"sakshi_proof_duration_seconds_count {len(durations)}",
                      f"sakshi_proof_duration_seconds_sum {sum(durations):.6f}",
                      "# HELP sakshi_queue_depth Number of queued jobs.", "# TYPE sakshi_queue_depth gauge",
                      f"sakshi_queue_depth {counts.get('QUEUED', 0)}",
                      "# HELP sakshi_outbox_pending Pending outbound messages.", "# TYPE sakshi_outbox_pending gauge",
                      f"sakshi_outbox_pending {pending_count}"])
        return "\n".join(lines) + "\n"

    @app.post("/v1/prove", status_code=202)
    def submit_proof_job(event: DecisionEvent, response: Response):
        # Validate schema at the API boundary so malformed events never enter the queue.
        try:
            validate_features(event.features)
            datetime.fromisoformat(event.ts.replace("Z", "+00:00"))
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not event.decision_id.strip() or not event.application_id.strip() or not event.policy_id.strip():
            raise HTTPException(status_code=422, detail="decision_id, application_id and policy_id must be non-empty")

        canonical_features = json.dumps({name: float(event.features[name]) for name in FEATURE_ORDER}, separators=(",", ":"))
        with SessionLocal() as session:
            existing = session.scalar(select(ProverJob).where(ProverJob.decision_id == event.decision_id))
            if existing is not None:
                same = (existing.application_id_hash == compute_application_hash(event.application_id) and existing.policy_id == event.policy_id
                        and existing.features_json == canonical_features and existing.decision == event.decision)
                if not same:
                    raise HTTPException(status_code=409, detail="decision_id already exists with different event content")
                response.headers["Idempotency-Replayed"] = "true"
                return {"job_id": existing.job_id, "decision_id": existing.decision_id, "status": existing.status}
            job_id = f"job_{uuid.uuid4().hex}"
            job = ProverJob(
                job_id=job_id, decision_id=event.decision_id, application_id_hash=compute_application_hash(event.application_id),
                policy_id=event.policy_id, features_json=canonical_features, decision=event.decision,
                status="QUEUED", created_at=utcnow(), updated_at=utcnow(),
            )
            session.add(job)
            try:
                session.commit()
            except Exception as exc:
                session.rollback()
                # Handle concurrent duplicate submissions deterministically.
                existing = session.scalar(select(ProverJob).where(ProverJob.decision_id == event.decision_id))
                if existing:
                    raise HTTPException(status_code=409, detail="concurrent duplicate decision_id submission") from exc
                raise HTTPException(status_code=500, detail="could not persist proving job") from exc
        response.headers["Location"] = f"/v1/jobs/{job_id}"
        return {"job_id": job_id, "decision_id": event.decision_id, "status": "QUEUED"}

    @app.get("/v1/jobs/{job_id}", response_model=JobStatus)
    def get_job_status(job_id: str):
        with SessionLocal() as session:
            job = session.get(ProverJob, job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            return JobStatus(
                job_id=job.job_id, decision_id=job.decision_id, status=job.status,
                error=job.error, created_at=job.created_at.isoformat(), updated_at=job.updated_at.isoformat(),
                proof_size_bytes=job.proof_size_bytes, proving_duration_ms=job.proving_duration_ms,
            )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.port)
