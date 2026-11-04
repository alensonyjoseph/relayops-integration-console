"""Create RelayOps workspace-scoped operational schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "shipments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("reference", sa.String(48), nullable=False),
        sa.Column("partner", sa.String(100), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "reference", name="uq_shipment_workspace_reference"),
    )
    op.create_index("ix_shipments_workspace_id", "shipments", ["workspace_id"])
    op.create_index("ix_shipments_reference", "shipments", ["reference"])
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("shipment_id", sa.String(36), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("external_id", sa.String(80), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("requested_status", sa.String(24), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("rejection_reason", sa.String(64), nullable=True),
        sa.Column("replay_count", sa.Integer(), nullable=False),
        sa.UniqueConstraint("workspace_id", "source", "external_id", name="uq_event_identity"),
    )
    op.create_index("ix_events_workspace_id", "events", ["workspace_id"])
    op.create_index("ix_events_shipment_id", "events", ["shipment_id"])
    op.create_table(
        "audit_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("shipment_id", sa.String(36), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("previous_status", sa.String(24), nullable=False),
        sa.Column("resulting_status", sa.String(24), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("reason", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_entries_workspace_id", "audit_entries", ["workspace_id"])
    op.create_index("ix_audit_entries_shipment_id", "audit_entries", ["shipment_id"])
    op.create_index("ix_audit_entries_event_id", "audit_entries", ["event_id"])

def downgrade():
    op.drop_table("audit_entries")
    op.drop_table("events")
    op.drop_table("shipments")
