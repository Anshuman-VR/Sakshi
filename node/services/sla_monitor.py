"""Fail-closed SLA expiration worker."""
import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from node.database import SessionLocal
from node.models import Decision
from node.services.ledger import LedgerService
from node.services.webhook_service import webhook_service


def expire_due_decisions(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    expired_count = 0
    with SessionLocal() as session:
        rows = session.execute(select(Decision).where(
            Decision.status == "NOTICE_RECEIVED", Decision.sla_deadline <= now
        ).with_for_update()).scalars().all()
        for decision in rows:
            # Recheck after acquiring row lock; only this transition is allowed.
            if decision.status != "NOTICE_RECEIVED" or decision.sla_deadline > now:
                continue
            verification_id = f"sla_{uuid.uuid4().hex}"
            decision.status = "EXPIRED"
            decision.failure_reason = "EXPIRED"
            decision.verified_at = now
            decision.verification_id = verification_id
            entry = LedgerService.append(session, decision.decision_id, verification_id,
                "EXPIRED", "EXPIRED", decision.policy_id, decision.model_commitment, None)
            decision.ledger_seq = entry.seq
            expired_count += 1
        session.commit()
        # Send after durable commit; delivery failures never roll back state.
        for decision in rows:
            if decision.status == "EXPIRED":
                try:
                    asyncio.run(webhook_service.send(decision, "SLA_BREACH"))
                except RuntimeError:
                    pass
    return expired_count


async def sla_monitor_loop(poll_seconds: float = 5.0) -> None:
    while True:
        await asyncio.sleep(poll_seconds)
        try:
            await asyncio.to_thread(expire_due_decisions)
        except Exception:
            # Worker must survive transient DB failures; health/readiness still
            # reports DB failure independently and the next pass retries.
            continue
