"""SQLAlchemy database/session lifecycle."""
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from node.config import config


def _make_engine(url: str):
    connect_args = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite:") else {}
    if url.startswith("sqlite:") and ":memory:" not in url:
        db_path = url.removeprefix("sqlite:///")
        if db_path and db_path != ":memory:":
            Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    eng = create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)
    if url.startswith("sqlite:"):
        @event.listens_for(eng, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    return eng


engine = _make_engine(config.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def init_db() -> None:
    # Import models so all metadata is registered before create_all.
    from node.models import Base  # noqa: F401
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        # Also install on databases created by earlier code versions where the
        # table already existed and SQLAlchemy's after_create hook won't rerun.
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger BEGIN SELECT RAISE(ABORT, 'audit ledger is append-only'); END")
            connection.exec_driver_sql("CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger BEGIN SELECT RAISE(ABORT, 'audit ledger is append-only'); END")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
