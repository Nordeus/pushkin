"""merge remove_device_id and message_blacklist

Revision ID: 822b8de2c260
Revises: 61e52d26ebea, 9ea5d4d49609
Create Date: 2016-06-23 10:13:56.776950

"""

# revision identifiers, used by Alembic.
revision = '822b8de2c260'
down_revision = ('61e52d26ebea', '9ea5d4d49609')
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    pass


def downgrade():
    pass
