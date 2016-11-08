"""centralized_db

Revision ID: 8b6104b8b8c0
Revises: 50db531bbf54
Create Date: 2016-08-02 12:08:09.560981

"""

# revision identifiers, used by Alembic.
revision = '8b6104b8b8c0'
down_revision = '67b14b57d9e4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

drop_func_get_and_update_messages_to_send = """DROP FUNCTION IF EXISTS "get_and_update_messages_to_send" (hstore[])"""

func_get_and_update_messages_to_send_old = """
CREATE OR REPLACE FUNCTION "get_and_update_messages_to_send" (
    p_mapping hstore[]
)
RETURNS hstore[] AS
$body$
DECLARE
  v_elligible_pairs hstore[];
BEGIN
    LOCK TABLE user_message_last_time_sent IN EXCLUSIVE MODE;
    SELECT INTO v_elligible_pairs * FROM get_elligible_user_message_pairs(p_mapping);
    PERFORM update_user_message_last_time_sent(v_elligible_pairs);

    RETURN v_elligible_pairs;
END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

func_get_and_update_messages_to_send = """
CREATE OR REPLACE FUNCTION "get_and_update_messages_to_send" (
    p_mapping hstore[]
)
RETURNS hstore[] AS
$body$
DECLARE
    v_elligible_pairs hstore[];
BEGIN
    PERFORM 1
    FROM login
    WHERE id IN (select cast(skeys(unnest(p_mapping)) as bigint))
    FOR UPDATE;

    SELECT INTO v_elligible_pairs * FROM get_elligible_user_message_pairs(p_mapping);
    PERFORM update_user_message_last_time_sent(v_elligible_pairs);

    RETURN v_elligible_pairs;
END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""


def upgrade():
    op.execute(drop_func_get_and_update_messages_to_send)
    op.execute(func_get_and_update_messages_to_send)


def downgrade():
    op.execute(drop_func_get_and_update_messages_to_send)
    op.execute(func_get_and_update_messages_to_send_old)
