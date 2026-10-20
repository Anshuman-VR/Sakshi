"""Tamper-evident append-only SHA-256 audit chain."""
import hashlib
import hmac
import json
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from node.models import LedgerEntry

GENESIS_HASH = "GENESIS_ROOT_HASH_SAKSHI_2026"


def _canonical_row(*, decision_id, verification_id, status, reason, policy_id,
                   model_commitment, proof_hash, ts) -> str:
    return json.dumps({
        "decision_id": decision_id,
        "verification_id": verification_id,
        "status": status,
        "reason": reason,
        "policy_id": policy_id,
        "model_commitment": model_commitment or "",
        "proof_hash": proof_hash,
        "ts": ts,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


class LedgerService:
    """Only exposes append and verification; deliberately no update/delete API."""

    @staticmethod
    def append(session: Session, decision_id: str, verification_id: str,
               status: str, reason: str | None, policy_id: str,
               model_commitment: str | None, proof_hash: str | None) -> LedgerEntry:
        # Caller owns transaction boundaries so decision/proof/ledger changes commit atomically.
        last = session.execute(select(LedgerEntry).order_by(LedgerEntry.seq.desc()).limit(1)).scalar_one_or_none()
        prev_hash = last.row_hash if last else GENESIS_HASH
        ts = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        row = {
            "decision_id": decision_id, "verification_id": verification_id,
            "status": status, "reason": reason, "policy_id": policy_id,
            "model_commitment": model_commitment or "", "proof_hash": proof_hash, "ts": ts,
        }
        row_hash = hashlib.sha256((prev_hash + _canonical_row(**row)).encode("utf-8")).hexdigest()
        entry = LedgerEntry(**row, prev_hash=prev_hash, row_hash=row_hash)
        session.add(entry)
        session.flush()
        return entry

    @staticmethod
    def verify_chain(session: Session) -> tuple[bool, int | None]:
        rows = session.execute(select(LedgerEntry).order_by(LedgerEntry.seq.asc())).scalars().all()
        expected_prev = GENESIS_HASH
        expected_seq = 1
        for row in rows:
            if row.seq != expected_seq or row.prev_hash != expected_prev:
                return False, row.seq
            row_data = {
                "decision_id": row.decision_id, "verification_id": row.verification_id,
                "status": row.status, "reason": row.reason, "policy_id": row.policy_id,
                "model_commitment": row.model_commitment or "", "proof_hash": row.proof_hash,
                "ts": row.ts,
            }
            expected_hash = hashlib.sha256((expected_prev + _canonical_row(**row_data)).encode("utf-8")).hexdigest()
            if not hmac.compare_digest(expected_hash, row.row_hash):
                return False, row.seq
            expected_prev = row.row_hash
            expected_seq += 1
        return True, None

    @staticmethod
    def current_sequence(session: Session) -> int:
        return int(session.execute(select(func.max(LedgerEntry.seq))).scalar_one_or_none() or 0)

    @staticmethod
    def export(session: Session, from_seq: int = 1, to_seq: int | None = None) -> dict:
        query = select(LedgerEntry).where(LedgerEntry.seq >= from_seq).order_by(LedgerEntry.seq.asc())
        if to_seq is not None:
            query = query.where(LedgerEntry.seq <= to_seq)
        rows = session.execute(query).scalars().all()
        valid, broken_at = LedgerService.verify_chain(session)
        return {"entries": [{k: getattr(row, k) for k in (
            "seq", "decision_id", "verification_id", "status", "reason", "policy_id",
            "model_commitment", "proof_hash", "ts", "prev_hash", "row_hash") } for row in rows],
            "chain_valid": valid, "broken_at_seq": broken_at,
            "ledger_seq": LedgerService.current_sequence(session)}
