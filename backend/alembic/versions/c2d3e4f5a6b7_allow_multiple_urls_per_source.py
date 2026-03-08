"""allow_multiple_urls_per_source

Revision ID: c2d3e4f5a6b7
Revises: b3c4d5e6f7a8
Create Date: 2026-03-09 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old unique index on (vinyl_id, source_id).
    # After merging, a single vinyl may legitimately have multiple listings
    # from the same source (different product URLs that turned out to be the
    # same record).  Without this change the merge deletes one of the
    # VinylSource rows, causing the crawler to re-scrape the lost URL on
    # every run.
    op.drop_index("ix_vinyl_source_vinyl_source", table_name="vinyl_source")

    # Re-create it as a non-unique index (still useful for lookups).
    op.create_index(
        "ix_vinyl_source_vinyl_source",
        "vinyl_source",
        ["vinyl_id", "source_id"],
        unique=False,
    )

    # Add a unique index on (external_url, source_id) so each URL is only
    # tracked once per source.
    op.create_index(
        "ix_vinyl_source_url",
        "vinyl_source",
        ["external_url", "source_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_vinyl_source_url", table_name="vinyl_source")
    op.drop_index("ix_vinyl_source_vinyl_source", table_name="vinyl_source")
    op.create_index(
        "ix_vinyl_source_vinyl_source",
        "vinyl_source",
        ["vinyl_id", "source_id"],
        unique=True,
    )
