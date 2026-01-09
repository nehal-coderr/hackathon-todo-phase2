"""Task ID: T014 - Create task table

Revision ID: 001
Revises:
Create Date: 2026-01-02

Per data-model.md and clarification session 2026-01-02:
- Task IDs are auto-increment integers (not UUIDs)
- user_id is UUID string from JWT
- Indexes for user_id and composite (user_id, created_at)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create task table with indexes and constraints."""
    op.create_table(
        "task",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("length(title) >= 1", name="chk_title_min_length"),
    )
    # Index for fast user task lookup (FR-012)
    op.create_index("ix_task_user_id", "task", ["user_id"])
    # Composite index for ordered task list (newest first)
    op.create_index("ix_task_user_created", "task", ["user_id", sa.text("created_at DESC")])


def downgrade() -> None:
    """Drop task table."""
    op.drop_index("ix_task_user_created", table_name="task")
    op.drop_index("ix_task_user_id", table_name="task")
    op.drop_table("task")
