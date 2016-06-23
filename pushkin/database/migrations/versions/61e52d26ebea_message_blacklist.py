'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

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
