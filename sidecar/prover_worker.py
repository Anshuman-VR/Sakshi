"""Durable asynchronous worker: queued event -> proof -> outbox -> lender node."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from sqlalchemy import select, update
from sidecar.config import config
from sidecar.database import SessionLocal
from sidecar.models import ProverJob, OutboxMessage, utcnow
from sidecar.outbox import process_outbox
from shared.types import FEATURE_ORDER, DecisionNotice
from circuits.prove import generate_zk_proof

log = logging.getLogger(__name__)


def _demo_model_commitment() -> str:
    configured = config.model_commitment.strip()
    if configured:
        return configured
    # Explicitly labelled demo-only value; never present this as a registered real model.
    return "0x" + hashlib.sha256(b"SAKSHI_DEMO_ONLY_MODEL_COMMITMENT_NOT_PRODUCTION").hexdigest()


def _policy_material(policy_id: str) -> tuple[str, str]:
    if config.policy_hash:
        return config.policy_hash, _demo_model_commitment()
    path = config.policy_path
    try:
        data = json.loads(open(path, "r", encoding="utf-8").read())
        from policy.sign import verify_policy
        if verify_policy(data):
            return str(data["policy_hash"]), str(data["model_commitment"])
        log.warning("Configured policy signatures did not validate; using demo-only policy hash")
    except Exception as exc:
        log.warning("Could not load signed policy %s: %s", path, exc)
    return hashlib.sha256(("SAKSHI_DEMO_POLICY:" + policy_id).encode()).hexdigest(), _demo_model_commitment()


def _enqueue_once(session, *, decision_id: str, endpoint: str, payload: dict) -> None:
    existing = session.scalar(select(OutboxMessage).where(
        OutboxMessage.decision_id == decision_id,
        OutboxMessage.target_endpoint == endpoint,
    ))
    if existing is None:
        session.add(OutboxMessage(
            decision_id=decision_id, target_endpoint=endpoint,
            payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            status="PENDING", attempts=0, next_retry_at=utcnow(),
        ))


async def process_one_job() -> bool:
    """Process at most one queued job. DB status transitions are restart-safe."""
    with SessionLocal() as session:
        candidate_id = session.scalar(select(ProverJob.job_id).where(
            ProverJob.status == "QUEUED"
        ).order_by(ProverJob.created_at.asc()).limit(1))
        if candidate_id is None:
            return False
        # Compare-and-set prevents two workers from claiming the same job.
        claimed = session.execute(update(ProverJob).where(
            ProverJob.job_id == candidate_id, ProverJob.status == "QUEUED"
        ).values(status="PROVING", updated_at=utcnow()))
        session.commit()
        if claimed.rowcount != 1:
            return False
        job = session.get(ProverJob, candidate_id)
        if job is None:
            return False
        job_id, decision_id, application_id_hash, policy_id, features_json, decision = (
            job.job_id, job.decision_id, job.application_id_hash, job.policy_id, job.features_json, job.decision
        )

    started = time.perf_counter()
    try:
        features = json.loads(features_json)
        # Validate ordering/schema before creating any proof or outbound payload.
        if list(features.keys()) != FEATURE_ORDER:
            # Dict key insertion order is not relied upon; the witness builder reads FEATURE_ORDER.
            missing = [key for key in FEATURE_ORDER if key not in features]
            extra = [key for key in features if key not in FEATURE_ORDER]
            if missing or extra:
                raise ValueError(f"feature schema mismatch; missing={missing}, extra={extra}")
        policy_hash, model_commitment = _policy_material(policy_id)
        proof_payload = generate_zk_proof(
            decision_id=decision_id, policy_id=policy_id, features=features, decision=decision,
            policy_hash=policy_hash, model_commitment=model_commitment, threshold=0.200,
            allow_mock=config.allow_mock_proofs,
        )
        proof_json = proof_payload.model_dump(mode="json")
        proof_bytes = __import__("base64").b64decode(proof_payload.proof)
        # Decision notice contains only an application hash, never raw application ID/features.
        notice = DecisionNotice(
            decision_id=decision_id,
            application_id_hash=application_id_hash,
            policy_id=policy_id,
            decision=decision,
            ts=datetime.now(timezone.utc).isoformat(),
        )
        with SessionLocal() as session:
            job = session.get(ProverJob, job_id)
            if job is None:
                return True
            job.proof_payload_json = json.dumps(proof_json, sort_keys=True, separators=(",", ":"))
            # Feature values are no longer needed after proof/outbox are persisted.
            job.features_json = "{}"
            job.proof_size_bytes = len(proof_bytes)
            job.proving_duration_ms = int((time.perf_counter() - started) * 1000)
            job.updated_at = utcnow()
            # Keep PROVING until the proof has actually been uploaded successfully.
            _enqueue_once(session, decision_id=decision_id, endpoint="/v1/decisions", payload=notice.model_dump(mode="json"))
            _enqueue_once(session, decision_id=decision_id, endpoint="/v1/proofs", payload=proof_json)
            session.commit()
        return True
    except Exception as exc:
        log.exception("Prover job %s failed", job_id)
        with SessionLocal() as session:
            job = session.get(ProverJob, job_id)
            if job is not None:
                job.status = "FAILED"
                job.error = f"{type(exc).__name__}: {exc}"[:4000]
                job.updated_at = utcnow()
                session.commit()
        return True


def recover_interrupted_jobs() -> int:
    """Requeue jobs interrupted before proof/outbox persistence completed."""
    with SessionLocal() as session:
        rows = session.scalars(select(ProverJob).where(
            ProverJob.status == "PROVING", ProverJob.proof_payload_json.is_(None)
        )).all()
        for job in rows:
            job.status = "QUEUED"
            job.error = None
            job.updated_at = utcnow()
        session.commit()
        return len(rows)


async def prover_loop(stop_event: asyncio.Event | None = None) -> None:
    """Worker loop. Jobs/outbox are durable; sleep is only polling cadence."""
    while stop_event is None or not stop_event.is_set():
        did_work = await process_one_job()
        try:
            await process_outbox()
        except Exception:
            log.exception("Outbox processing pass failed; durable messages will be retried")
        if not did_work:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=0.5) if stop_event else await asyncio.sleep(0.5)
            except asyncio.TimeoutError:
                pass
