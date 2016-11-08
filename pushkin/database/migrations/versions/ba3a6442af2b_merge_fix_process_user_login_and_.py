"""merge fix_process_user_login and database_permission

Revision ID: ba3a6442af2b
Revises: 50db531bbf54, 70ad8e4607cd
Create Date: 2016-08-04 12:10:11.869905

"""

# revision identifiers, used by Alembic.
revision = 'ba3a6442af2b'
down_revision = ('50db531bbf54', '70ad8e4607cd')
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    pass


def downgrade():
    pass
