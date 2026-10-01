"""Create platform administration foundation.

Revision ID: 20261001_0001
Revises:
Create Date: 2026-10-01
"""

from alembic import op

import app.modules.companies.models  # noqa: F401 - registers all platform tables
from app.core.database import Base

revision = "20261001_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The schema uses standard PostgreSQL types today. A later geospatial
    # migration will enable PostGIS in environments where it is installed.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
