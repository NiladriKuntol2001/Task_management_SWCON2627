"""add is_admin/is_active to users, completed_at to tasks

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "tasks",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill: tasks already completed get their last-updated time as a best guess.
    op.execute("UPDATE tasks SET completed_at = updated_at WHERE completed = true")


def downgrade() -> None:
    op.drop_column("tasks", "completed_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "is_admin")
