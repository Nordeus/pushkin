"""database permission

Revision ID: 50db531bbf54
Revises: 822b8de2c260
Create Date: 2016-08-01 11:50:51.872278

"""

# revision identifiers, used by Alembic.
revision = '50db531bbf54'
down_revision = '822b8de2c260'
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO public;")


def downgrade():
    pass
