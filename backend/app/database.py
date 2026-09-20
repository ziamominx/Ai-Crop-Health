"""SQLAlchemy engine/session + declarative base.

Primary: PostgreSQL via DATABASE_URL (default in .env.example).
Zero-setup fallback: if PostgreSQL is unreachable and SQLITE_FALLBACK=true,
a local SQLite file is used so academic demos always run (a loud warning is
printed and surfaced via /api/health).
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_is_fallback_db = False


def _resolve_url() -> str:
    global _is_fallback_db
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        return url
    if not settings.SQLITE_FALLBACK:
        return url
    # Probe PostgreSQL; fall back to SQLite only if it is genuinely unreachable.
    try:
        probe = create_engine(url, pool_pre_ping=True)
        with probe.connect() as conn:
            conn.execute(text("SELECT 1"))
        probe.dispose()
        return url
    except Exception as exc:
        _is_fallback_db = True
        fallback = "sqlite:///./agricure_dev.db"
        print("=" * 70)
        print(f"[Agricure] WARNING: PostgreSQL unavailable ({str(exc)[:120]}).")
        print(f"[Agricure] Falling back to local SQLite demo database: {fallback}")
        print("[Agricure] For the real PostgreSQL setup see README.md (Step 2).")
        print("=" * 70)
        return fallback


DATABASE_URL_RESOLVED = _resolve_url()

connect_args = {}
if DATABASE_URL_RESOLVED.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL_RESOLVED,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
