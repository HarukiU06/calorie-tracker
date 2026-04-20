from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base

DB_PATH = Path(__file__).parent.parent.parent / "data.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal: sessionmaker[Session] = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(ENGINE)


def get_session() -> Session:
    return SessionLocal()
