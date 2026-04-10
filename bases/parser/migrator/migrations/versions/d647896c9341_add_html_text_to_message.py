"""Add html text to message

Revision ID: d647896c9341
Revises: d2c2fc33083a
Create Date: 2026-04-09 16:16:26.309582

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d647896c9341"
down_revision: str | Sequence[str] | None = "d2c2fc33083a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("channel_message", sa.Column("html_text", sa.Text(), nullable=True))
    op.execute("UPDATE channel_message SET html_text = text")
    op.alter_column(
        "channel_message", "html_text", existing_type=sa.Text(), nullable=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("channel_message", "html_text")
