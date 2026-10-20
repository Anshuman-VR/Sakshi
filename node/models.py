"""Persistent domain models. Shared API contracts remain in shared.types."""
from datetime import datetime, timezone
from sqlalchemy import (DateTime, Float, ForeignKey, Index, Integer,
                        LargeBinary, String, Text, JSON, UniqueConstraint, event, DDL)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.exc import InvalidRequestError


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class RegisteredModel(Base):
    __tablename__ = "registered_models"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    commitment: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    circuit_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    vk: Mapped[str] = mapped_column(Text, nullable=False)
    feature_schema_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    parity_report: Mapped[dict] = mapped_column(JSON, nullable=False)
    lsp_sig: Mapped[str] = mapped_column(Text, nullable=False)
    lsp_pubkey: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_APPROVAL", index=True)
    lender_sig: Mapped[str | None] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    grace_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Policy(Base):
    __tablename__ = "policies"
    policy_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    lender_id: Mapped[str] = mapped_column(String(128), nullable=False)
    lsp_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product: Mapped[str] = mapped_column(String(128), nullable=False)
    model_commitment: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    circuit_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    feature_schema_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    decision_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    fixed_point_scale: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    hard_rules: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    proof_sla_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    lsp_sig: Mapped[str] = mapped_column(Text, nullable=False)
    lender_sig: Mapped[str] = mapped_column(Text, nullable=False)
    lsp_pubkey: Mapped[str] = mapped_column(String(128), nullable=False)
    lender_pubkey: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_document: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE", index=True)


class Decision(Base):
    __tablename__ = "decisions"
    decision_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    application_id_hash: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.policy_id"), nullable=False, index=True)
    decision: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOTICE_RECEIVED", index=True)
    sla_deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_commitment: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ledger_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ProofRecord(Base):
    __tablename__ = "proof_records"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.decision_id"), nullable=False, index=True)
    proof_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    proof_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    public_inputs: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class LedgerEntry(Base):
    __tablename__ = "ledger"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    verification_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    policy_id: Mapped[str] = mapped_column(String(256), nullable=False)
    model_commitment: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    proof_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ts: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    __table_args__ = (Index("ix_ledger_seq_status", "seq", "status"),)


class InputBinding(Base):
    __tablename__ = "input_bindings"
    __table_args__ = (UniqueConstraint("decision_id", name="uq_input_binding_decision"),)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    application_id_hash: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    x_prime: Mapped[str] = mapped_column(String(256), nullable=False)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.decision_id"), nullable=False, index=True)
    bound_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    binding_status: Mapped[str] = mapped_column(String(32), nullable=False)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String(256), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


# Guard ORM mutation paths. Raw SQL/database-admin access remains outside the
# application trust boundary and is detected by the hash-chain verifier.
@event.listens_for(LedgerEntry, "before_update")
def _prevent_ledger_update(_mapper, _connection, _target):
    raise InvalidRequestError("Audit ledger is append-only; updates are forbidden")


@event.listens_for(LedgerEntry, "before_delete")
def _prevent_ledger_delete(_mapper, _connection, _target):
    raise InvalidRequestError("Audit ledger is append-only; deletes are forbidden")


# SQLite lacks table-level user grants, so install defensive database triggers
# as well as ORM guards. Privileged tamper tests explicitly drop these triggers
# to emulate an administrator who can bypass the application boundary.
event.listen(LedgerEntry.__table__, "after_create", DDL(
    "CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger "
    "BEGIN SELECT RAISE(ABORT, 'audit ledger is append-only'); END"
).execute_if(dialect="sqlite"))
event.listen(LedgerEntry.__table__, "after_create", DDL(
    "CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger "
    "BEGIN SELECT RAISE(ABORT, 'audit ledger is append-only'); END"
).execute_if(dialect="sqlite"))
