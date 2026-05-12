from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from .models import Base
from .migrations import run_migrations

def _normalize_sqlite_url(url: str) -> str:
    if not url.startswith("sqlite:///"):
        return url

    raw_path = url.replace("sqlite:///", "", 1)
    path = Path(raw_path)
    if path.is_absolute():
        return url

    base_dir = Path(__file__).resolve().parents[1]
    abs_path = (base_dir / path).resolve()
    return f"sqlite:///{abs_path.as_posix()}"


DATABASE_URL = _normalize_sqlite_url(settings.database_url)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
