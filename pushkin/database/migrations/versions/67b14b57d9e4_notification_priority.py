"""notification priority

Revision ID: 67b14b57d9e4
Revises: ba3a6442af2b
Create Date: 2016-10-31 09:02:50.930136

"""

# revision identifiers, used by Alembic.
revision = '67b14b57d9e4'
down_revision = 'ba3a6442af2b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('message', sa.Column('priority', sa.Text(), nullable=False, default='normal'))


def downgrade():
    op.drop_column('message', 'priority')
