"""Durable at-least-once delivery with bounded exponential retry delay."""
from __future__ import annotations

import asyncio
import json
import hashlib
from urllib.parse import urlparse
from datetime import datetime, timedelta
import httpx
from sqlalchemy import select
from sidecar.config import config
from sidecar.database import SessionLocal
from sidecar.models import OutboxMessage, ProverJob, utcnow


async def process_outbox(*, client: httpx.AsyncClient | None = None, limit: int = 25) -> int:
    """Attempt due messages in creation order; proof delivery waits for notice delivery.

    Messages remain durable across process restarts. Failures never cause a silent
    drop; they are retried with exponential backoff capped by retry_max_seconds.
    """
    now = utcnow()
    with SessionLocal() as session:
        messages = session.scalars(
            select(OutboxMessage)
            .where(OutboxMessage.status == "PENDING", OutboxMessage.next_retry_at <= now)
            .order_by(OutboxMessage.id.asc()).limit(limit)
        ).all()
        # Snapshot fields before the DB session is released during network I/O.
        batch = [(m.id, m.decision_id, m.target_endpoint, m.payload_json, m.attempts) for m in messages]

    if not batch:
        return 0

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=config.request_timeout_seconds)
    assert client is not None
    processed = 0
    try:
        for message_id, decision_id, endpoint, payload_json, previous_attempts in batch:
            with SessionLocal() as session:
                current = session.get(OutboxMessage, message_id)
                if current is None or current.status != "PENDING":
                    continue
                if endpoint == "/v1/proofs":
                    notice = session.scalar(select(OutboxMessage).where(
                        OutboxMessage.decision_id == decision_id,
                        OutboxMessage.target_endpoint == "/v1/decisions",
                    ))
                    if notice is not None and notice.status != "DELIVERED":
                        continue
                current.attempts += 1
                attempt_number = current.attempts
                session.commit()

            target_url = f"{config.lender_node_url.rstrip('/')}{endpoint}"
            headers = {
                "Content-Type": "application/json",
                "X-Sakshi-Key": config.sidecar_api_key,
                "Idempotency-Key": hashlib.sha256(f"{decision_id}:{endpoint}".encode("utf-8")).hexdigest(),
            }
            try:
                require_https = __import__("os").getenv("SAKSHI_SIDECAR_REQUIRE_HTTPS", "false").strip().lower() in {"1", "true", "yes"}
                if require_https and urlparse(target_url).scheme != "https":
                    raise RuntimeError("SAKSHI_SIDECAR_REQUIRE_HTTPS is enabled but lender URL is not HTTPS")
                response = await client.post(
                    target_url, json=json.loads(payload_json), headers=headers,
                )
                response.raise_for_status()
                if response.status_code not in (200, 201, 202, 204):
                    raise RuntimeError(f"unexpected response status {response.status_code}")
                with SessionLocal() as session:
                    current = session.get(OutboxMessage, message_id)
                    if current is not None:
                        current.status = "DELIVERED"
                        current.delivered_at = utcnow()
                        current.last_error = None
                    if endpoint == "/v1/proofs":
                        job = session.scalar(select(ProverJob).where(ProverJob.decision_id == decision_id))
                        if job is not None:
                            job.status = "UPLOADED"
                            job.updated_at = utcnow()
                    session.commit()
            except Exception as exc:
                delay = min(config.retry_max_seconds, config.retry_base_seconds * (2 ** min(attempt_number - 1, 16)))
                with SessionLocal() as session:
                    current = session.get(OutboxMessage, message_id)
                    if current is not None and current.status == "PENDING":
                        current.next_retry_at = utcnow() + timedelta(seconds=delay)
                        current.last_error = f"{type(exc).__name__}: {exc}"[:2000]
                    session.commit()
            processed += 1
    finally:
        if own_client:
            await client.aclose()
    return processed
