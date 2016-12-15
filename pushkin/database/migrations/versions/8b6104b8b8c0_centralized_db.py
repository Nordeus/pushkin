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
drop_func_upsert_user_message_last_time_sent = """DROP FUNCTION IF EXISTS "upsert_user_message_last_time_sent" (bigint, int)"""

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
CREATE OR REPLACE FUNCTION "get_non_elligible_user_message_pairs" (
    p_users bigint[]
)
RETURNS SETOF "public"."user_message_last_time_sent" AS
$body$
BEGIN
        RETURN QUERY SELECT
            0,
            l.id,
            m.id,
            0::bigint
        FROM login l
        LEFT JOIN user_message_last_time_sent umlts
          ON l.id = umlts.login_id
        LEFT JOIN message m
          ON m.id = umlts.message_id
        WHERE
            l.id = ANY(p_users) AND
            umlts.last_time_sent_ts_bigint + m.cooldown_ts > extract(epoch from current_timestamp)::bigint*1000;

END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

func_upsert_user_message_last_time_sent = """
CREATE OR REPLACE FUNCTION "upsert_user_message_last_time_sent" (
    p_login_id BIGINT,
    p_message_id INT
)
RETURNS "pg_catalog"."void" AS
$body$
BEGIN
        WITH new_value (login_id, message_id, last_time_sent_ts_bigint) AS (
            values  (p_login_id, p_message_id, extract(epoch from current_timestamp)::bigint*1000)
        ),
        upsert as (
            UPDATE user_message_last_time_sent umlts
            SET last_time_sent_ts_bigint = nv.last_time_sent_ts_bigint
            FROM new_value nv
            WHERE umlts.login_id = nv.login_id AND umlts.message_id = nv.message_id
            RETURNING nv.*
        )
        INSERT INTO user_message_last_time_sent (login_id, message_id, last_time_sent_ts_bigint)
        SELECT login_id, message_id, last_time_sent_ts_bigint
        FROM new_value nv
        WHERE NOT EXISTS (SELECT 1 FROM upsert u WHERE u.login_id = nv.login_id AND message_id = nv.message_id);

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
    op.execute(func_upsert_user_message_last_time_sent)


def downgrade():
    op.execute(drop_func_get_and_update_messages_to_send)
    op.execute(func_get_and_update_messages_to_send_old)
    op.execute(drop_func_upsert_user_message_last_time_sent)
