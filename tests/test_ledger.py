"""Append-only ledger integrity tests."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import InvalidRequestError
from node.models import LedgerEntry
from node.services.ledger import LedgerService, GENESIS_HASH


def test_chain_integrity_valid(environment):
    with environment["session"]() as db:
        for i in range(5):
            LedgerService.append(db, f"d{i}", f"v{i}", "FAILED", "TEST", "p1", "c1", f"{i:064x}")
        db.commit()
        assert LedgerService.verify_chain(db) == (True, None)


def test_chain_tamper_detected(environment):
    with environment["session"]() as db:
        for i in range(5):
            LedgerService.append(db, f"d{i}", f"v{i}", "FAILED", "TEST", "p1", "c1", f"{i:064x}")
        db.commit()
        # Simulate a privileged database administrator bypassing application
        # protections; ordinary SQL updates are blocked by the SQLite trigger.
        db.execute(text("DROP TRIGGER ledger_no_update"))
        db.execute(text("UPDATE ledger SET reason='ALTERED' WHERE seq=3"))
        db.commit()
        assert LedgerService.verify_chain(db) == (False, 3)


def test_ledger_orm_update_is_blocked(environment):
    with environment["session"]() as db:
        row = LedgerService.append(db, "d1", "v1", "FAILED", "TEST", "p1", "c1", "1" * 64)
        db.commit()
        row.status = "VERIFIED"
        with pytest.raises(InvalidRequestError, match="append-only"):
            db.flush()
        db.rollback()


def test_genesis_hash_is_first_prev_hash(environment):
    with environment["session"]() as db:
        row = LedgerService.append(db, "d1", "v1", "FAILED", "TEST", "p1", "c1", "1" * 64)
        db.commit()
        assert row.prev_hash == GENESIS_HASH
        assert len(row.row_hash) == 64


def test_deleted_middle_record_detected(environment):
    with environment["session"]() as db:
        for i in range(4):
            LedgerService.append(db, f"d{i}", f"v{i}", "FAILED", "TEST", "p1", "c1", f"{i:064x}")
        db.commit()
        db.execute(text("DROP TRIGGER ledger_no_delete"))
        db.execute(text("DELETE FROM ledger WHERE seq=2"))
        db.commit()
        valid, broken_at = LedgerService.verify_chain(db)
        assert valid is False and broken_at == 3


def test_sql_updates_and_deletes_are_blocked_by_database(environment):
    with environment["session"]() as db:
        LedgerService.append(db, "d1", "v1", "FAILED", "TEST", "p1", "c1", "1" * 64)
        db.commit()
        with pytest.raises(Exception, match="audit ledger is append-only"):
            db.execute(text("UPDATE ledger SET reason='ALTERED' WHERE seq=1"))
        db.rollback()
        with pytest.raises(Exception, match="audit ledger is append-only"):
            db.execute(text("DELETE FROM ledger WHERE seq=1"))
        db.rollback()
