"""ttl

Revision ID: 866d344d7b5d
Revises: e2a42bcd4c02
Create Date: 2016-05-17 11:34:02.902400

"""

# revision identifiers, used by Alembic.
revision = '866d344d7b5d'
down_revision = 'e2a42bcd4c02'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('message', sa.Column('expiry_millis', sa.BigInteger))


def downgrade():
    op.drop_column('message', 'expiry_millis')
