"""Database mappings and engine creation. No silent production schema creation."""
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def uid() -> str:
    return str(uuid.uuid4())

class Base(DeclarativeBase):
    pass

class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (UniqueConstraint("workspace_id", "reference", name="uq_shipment_workspace_reference"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    reference: Mapped[str] = mapped_column(String(48), index=True)
    partner: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(24), default="CREATED")
    version: Mapped[int] = mapped_column(Integer, default=0)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    events: Mapped[list["Event"]] = relationship(back_populates="shipment")

class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("workspace_id", "source", "external_id", name="uq_event_identity"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"), index=True)
    source: Mapped[str] = mapped_column(String(80))
    external_id: Mapped[str] = mapped_column(String(80))
    payload_hash: Mapped[str] = mapped_column(String(64))
    requested_status: Mapped[str] = mapped_column(String(24))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    outcome: Mapped[str] = mapped_column(String(24))
    rejection_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    replay_count: Mapped[int] = mapped_column(Integer, default=0)
    shipment: Mapped[Shipment] = relationship(back_populates="events")

class AuditEntry(Base):
    __tablename__ = "audit_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    previous_status: Mapped[str] = mapped_column(String(24))
    resulting_status: Mapped[str] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

def normalize_url(url: str | None) -> str | None:
    if url and url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url and url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url

def create_database_engine(url: str | None = None):
    url = normalize_url(url or os.getenv("DATABASE_URL"))
    if not url:
        return None
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    else:
        options.update(pool_size=3, max_overflow=2, pool_recycle=280)
    return create_engine(url, **options)

def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
