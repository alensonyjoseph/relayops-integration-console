"""Opt-in migration bootstrap for a *dedicated, synthetic* public demo DB.

Not for customer data. The PostgreSQL transaction-level advisory lock serialises
multiple Vercel cold starts, including through transactional connection pools.
"""
import threading
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

MIGRATION_LOCK_ID = 741291805

class DemoSchemaInitializer:
    def __init__(self, engine):
        self.engine = engine
        self._guard = threading.Lock()
        self._ready = False

    def ensure(self):
        if self._ready:
            return
        with self._guard:
            if self._ready:
                return
            with self.engine.connect() as conn:
                try:
                    if self.engine.dialect.name == "postgresql":
                        # Lock is released by commit/rollback, not pinned to a pooled session.
                        conn.execute(text("SELECT pg_advisory_xact_lock(:id)"),
                                     {"id": MIGRATION_LOCK_ID})
                    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
                    cfg.attributes["connection"] = conn
                    command.upgrade(cfg, "head")
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
            self._ready = True
