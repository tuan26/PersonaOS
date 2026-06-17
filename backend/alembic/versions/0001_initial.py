"""Alembic migration script template."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema for all models."""
    # Tables are created via Base.metadata.create_all on startup
    # This file serves as the baseline for future migrations
    pass


def downgrade() -> None:
    """Revert initial schema."""
    pass
