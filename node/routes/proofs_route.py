"""Idempotent proof intake and background verification/ledger commit."""
import hashlib, json, uuid, time
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from shared.types import ProofPayload
from node.config import config
from node.database import SessionLocal, get_db
from node.models import Decision, IdempotencyKey, ProofRecord
from node.routes.deps import require_sidecar
from node.services.ledger import LedgerService
from node.services.verifier import VerifierEngine, proof_digest
from node.services.webhook_service import webhook_service
from node.services.metrics import observe_verification_duration

router = APIRouter(tags=["proof verification"])


def process_proof(payload_data: dict, verification_id: str, proof_hash: str, reserved: bool) -> None:
    """Background worker uses its own session and commits state + ledger atomically."""
    with SessionLocal() as db:
        payload = ProofPayload.model_validate(payload_data)
        try:
            started = time.perf_counter()
            try:
                result = VerifierEngine.run_pipeline(db, payload, verification_id=verification_id)
            finally:
                observe_verification_duration(time.perf_counter() - started)
            record = db.get(ProofRecord, verification_id) if reserved else None
            if record is not None:
                record.status = result.status
                record.reason = result.reason
            decision = db.get(Decision, payload.decision_id)
            if decision is not None and decision.status == "NOTICE_RECEIVED":
                decision.status = result.status
                decision.failure_reason = result.reason
                decision.model_commitment = payload.public_inputs.C
                decision.verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
                decision.verification_id = result.verification_id
            entry = LedgerService.append(db, payload.decision_id, result.verification_id,
                result.status, result.reason, payload.policy_id, payload.public_inputs.C, proof_hash)
            if decision is not None and decision.status in {"VERIFIED", "FAILED"} and decision.verification_id == result.verification_id:
                decision.ledger_seq = entry.seq
            db.commit()
            if result.status == "FAILED" and decision is not None:
                try:
                    import asyncio
                    asyncio.run(webhook_service.send(decision, "VERIFICATION_FAILED"))
                except RuntimeError:
                    pass
        except IntegrityError:
            db.rollback()
            # A concurrent duplicate is fail-closed. The unique proof record is
            # the replay guard; avoid creating a second ledger row with same ID.
        except Exception:
            db.rollback()
            # Persist an operational failure rather than leave a decision authorized.
            decision = db.get(Decision, payload.decision_id)
            if decision is not None and decision.status == "NOTICE_RECEIVED":
                decision.status = "FAILED"
                decision.failure_reason = "INVALID_PROOF"
                decision.verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
                decision.verification_id = verification_id
                try:
                    LedgerService.append(db, payload.decision_id, verification_id, "FAILED",
                        "INVALID_PROOF", payload.policy_id, payload.public_inputs.C, proof_hash)
                    db.commit()
                except Exception:
                    db.rollback()


@router.post("/v1/proofs", status_code=202)
def submit_proof(payload: ProofPayload, background_tasks: BackgroundTasks,
                 idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=256),
                 _auth=Depends(require_sidecar), db: Session = Depends(get_db)):
    proof_bytes, proof_hash, encoding_valid = proof_digest(payload)
    measured_size = len(proof_bytes) if encoding_valid else len(payload.proof.encode("utf-8"))
    if measured_size > config.proof_max_bytes:
        raise HTTPException(413, "PROOF_TOO_LARGE")
    if db.get(Decision, payload.decision_id) is None:
        raise HTTPException(404, "DECISION_NOT_FOUND")
    request_hash = hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()
    existing_key = db.get(IdempotencyKey, idempotency_key)
    if existing_key is not None:
        if existing_key.request_hash != request_hash:
            raise HTTPException(409, "IDEMPOTENCY_KEY_REUSED")
        return existing_key.response

    verification_id = f"v_{uuid.uuid4().hex}"
    reserved = False
    if db.execute(select(ProofRecord.id).where(ProofRecord.proof_hash == proof_hash)).first() is None:
        # Store exact decoded bytes for valid base64, raw submitted bytes otherwise.
        blob = proof_bytes if encoding_valid else payload.proof.encode("utf-8")
        db.add(ProofRecord(id=verification_id, decision_id=payload.decision_id,
            proof_hash=proof_hash, proof_blob=blob,
            public_inputs=payload.public_inputs.model_dump(mode="json"), status="PENDING"))
        try:
            db.flush()
            reserved = True
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "REPLAY")
    response = {"verification_id": verification_id, "status": "PENDING"}
    db.add(IdempotencyKey(key=idempotency_key, request_hash=request_hash, response=response))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        key_row = db.get(IdempotencyKey, idempotency_key)
        if key_row and key_row.request_hash == request_hash:
            return key_row.response
        raise HTTPException(409, "IDEMPOTENCY_KEY_REUSED")
    background_tasks.add_task(process_proof, payload.model_dump(mode="json"), verification_id, proof_hash, reserved)
    return response
