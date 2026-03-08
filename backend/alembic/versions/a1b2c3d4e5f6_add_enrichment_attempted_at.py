"""add_enrichment_attempted_at

Revision ID: a1b2c3d4e5f6
Revises: f207bff6ac77
Create Date: 2026-03-08 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f207bff6ac77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vinyl", sa.Column("enrichment_attempted_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("vinyl", "enrichment_attempted_at")
