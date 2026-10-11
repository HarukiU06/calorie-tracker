import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base

DB_PATH = Path(__file__).parent.parent.parent / "data.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal: sessionmaker[Session] = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)


def init_db() -> None:
    # The DB holds personal health data; keep it readable by the owner only.
    DB_PATH.touch(mode=0o600, exist_ok=True)
    os.chmod(DB_PATH, 0o600)
    Base.metadata.create_all(ENGINE)


def get_session() -> Session:
    return SessionLocal()
