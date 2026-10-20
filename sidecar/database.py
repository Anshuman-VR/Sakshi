"""SQLite database lifecycle. SQLite is local to the LSP zone only."""
from __future__ import annotations
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sidecar.config import config
from sidecar.models import Base


def _make_engine(db_path: str):
    if db_path.startswith("sqlite:"):
        url = db_path
    else:
        Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{Path(db_path).expanduser().resolve()}"
    return create_engine(url, connect_args={"check_same_thread": False}, pool_pre_ping=True)


engine = _make_engine(config.db_path)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def reset_engine_for_tests(db_path: str):
    """Replace the engine/session factory; intended for isolated tests only."""
    global engine, SessionLocal
    engine.dispose()
    engine = _make_engine(db_path)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return engine
