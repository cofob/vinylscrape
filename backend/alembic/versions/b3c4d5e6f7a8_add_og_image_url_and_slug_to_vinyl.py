"""add_og_image_url_and_slug_to_vinyl

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-08 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vinyl", sa.Column("og_image_url", sa.Text(), nullable=True))
    op.add_column("vinyl", sa.Column("slug", sa.String(600), nullable=True))
    op.create_unique_constraint("uq_vinyl_slug", "vinyl", ["slug"])


def downgrade() -> None:
    op.drop_constraint("uq_vinyl_slug", "vinyl", type_="unique")
    op.drop_column("vinyl", "slug")
    op.drop_column("vinyl", "og_image_url")
