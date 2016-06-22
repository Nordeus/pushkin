"""message_blacklist

Revision ID: 61e52d26ebea
Revises: 866d344d7b5d
Create Date: 2016-06-21 11:41:46.919707

"""

# revision identifiers, used by Alembic.
revision = '61e52d26ebea'
down_revision = '866d344d7b5d'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    context = op.get_context()
    connection = op.get_bind()

    if not context.dialect.has_table(connection.engine, 'message_blacklist'):
        op.create_table('message_blacklist',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('login_id', sa.BigInteger(), nullable=False),
            sa.Column('blacklist', postgresql.ARRAY(sa.Integer)),
            sa.ForeignKeyConstraint(['login_id'], ['login.id'], ondelete='CASCADE', name="ref_message_blacklist_login_id_to_login"),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('idx_message_blacklist_login_id'), 'message_blacklist', ['login_id'], unique=True)


def downgrade():
    op.drop_index(op.f('idx_message_blacklist_login_id'), table_name='message_blacklist')
    op.drop_table('message_blacklist')
