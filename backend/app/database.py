"""SQLAlchemy engine/session + declarative base.

Primary: PostgreSQL via DATABASE_URL (default in .env.example).
Zero-setup fallback: if PostgreSQL is unreachable and SQLITE_FALLBACK=true,
a local SQLite file is used so academic demos always run (a loud warning is
printed and surfaced via /api/health).

On read-only serverless filesystems (e.g. Vercel functions, where only /tmp is
writable) the fallback file is placed in a temp directory instead of the CWD —
note such a database is EPHEMERAL and dies with the instance; set DATABASE_URL
to a hosted PostgreSQL (Neon/Supabase) for real persistence.
"""
import os
import tempfile

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_is_fallback_db = False


def _sqlite_fallback_url() -> str:
    """A writable SQLite location: CWD normally, temp dir on serverless/RO filesystems."""
    probe_file = None
    try:
        probe_file = tempfile.NamedTemporaryFile(prefix="agricure_w_", delete=False)
        writable = True
    except (OSError, PermissionError):
        writable = False
    finally:
        if probe_file is not None:
            try:
                os.unlink(probe_file.name)
            except OSError:
                pass
    if writable:
        return "sqlite:///./agricure_dev.db"
    tmp_dir = os.path.join(tempfile.gettempdir(), "agricure")
    os.makedirs(tmp_dir, exist_ok=True)
    return f"sqlite:///{os.path.join(tmp_dir, 'agricure_dev.db').replace(os.sep, '/')}"


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
        fallback = _sqlite_fallback_url()
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
