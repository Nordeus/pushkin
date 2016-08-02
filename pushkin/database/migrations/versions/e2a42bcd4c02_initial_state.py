'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

# revision identifiers, used by Alembic.
revision = 'e2a42bcd4c02'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from pushkin.database import model

func_process_user_login = """
CREATE OR REPLACE FUNCTION "process_user_login" (
    p_login_id int8,
    p_language_id int2,
    p_platform_id int2,
    p_device_id text,
    p_device_token text,
    p_application_version int4
)
RETURNS "pg_catalog"."void" AS
$body$
BEGIN
    WITH
    data(login_id, language_id) AS (
        VALUES(p_login_id, p_language_id)
    ),
    update_part AS (
        UPDATE login
        SET language_id = d.language_id
        FROM data d
        WHERE login.id = d.login_id
        RETURNING d.*
    )
    INSERT INTO login
    (id, language_id)
    SELECT d.login_id, d.language_id
    FROM data d
    WHERE NOT EXISTS (
        SELECT 1
        FROM update_part u
        WHERE u.login_id = d.login_id);

    WITH
    data_tmp(login_id, platform_id, device_id, device_token, application_version) AS (
        VALUES(p_login_id, p_platform_id, p_device_id, p_device_token, p_application_version)
    ),
    data AS (
        SELECT * FROM data_tmp WHERE device_id IS NOT NULL AND device_token IS NOT NULL
    ),
    update_part AS (
        UPDATE device
        SET device_token = d.device_token,
            device_token_new = CASE WHEN device.device_token <> d.device_token THEN NULL ELSE device.device_token_new END,
            application_version = d.application_version
        FROM data d
        WHERE device.device_id = d.device_id
            AND device.login_id = d.login_id
            AND device.platform_id = d.platform_id
        RETURNING d.*
    )
    INSERT INTO device(login_id, platform_id, device_id, device_token, application_version)
    SELECT d.login_id, d.platform_id, d.device_id, d.device_token, d.application_version
    FROM data d
    WHERE NOT EXISTS (
        SELECT 1
        FROM update_part u
        WHERE u.login_id = d.login_id
            AND u.platform_id = d.platform_id
            AND u.device_id = d.device_id);

END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

drop_func_process_user_login = """DROP FUNCTION IF EXISTS "process_user_login" (int8, int2, int2, text, text, int4)"""

func_get_elligible_user_message_pairs = """
CREATE OR REPLACE FUNCTION "get_elligible_user_message_pairs" (
    p_mapping hstore[]
)
RETURNS hstore[] AS
$body$
DECLARE
  v_elligible_pairs hstore[];
BEGIN
        WITH hstores AS (
            SELECT UNNEST(p_mapping) pair
        ),
        pairs AS (
            SELECT DISTINCT
                (EACH(pair)).key::int8 login_id,
                (EACH(pair)).value::int4 message_id
            FROM hstores
        ),
        eligible AS (
            SELECT
                p.login_id,
                p.message_id
            FROM pairs p
            INNER JOIN message m ON
                p.message_id = m.id
            LEFT JOIN user_message_last_time_sent umlts ON
                umlts.login_id = p.login_id AND umlts.message_id = p.message_id
            WHERE
                m.cooldown_ts IS NULL OR
                umlts.last_time_sent_ts_bigint IS NULL OR
                umlts.last_time_sent_ts_bigint + m.cooldown_ts < extract(epoch from current_timestamp)::bigint*1000
        )
        SELECT INTO v_elligible_pairs
        ARRAY_AGG(HSTORE(login_id::TEXT, message_id::TEXT))
        FROM eligible;

        RETURN v_elligible_pairs;

END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

drop_func_get_elligible_user_message_pairs = """DROP FUNCTION IF EXISTS "get_elligible_user_message_pairs" (hstore[])"""

func_update_user_message_last_time_sent = """
CREATE OR REPLACE FUNCTION "update_user_message_last_time_sent" (
    p_mapping hstore[]
)
RETURNS "pg_catalog"."void" AS
$body$
BEGIN
        WITH hstores AS (
            SELECT UNNEST(p_mapping) pair
        ),
        pairs AS (
            SELECT (EACH(pair)).key::int8 login_id, (EACH(pair)).value::int4 message_id
            FROM hstores
        ),
        upsert AS (
            UPDATE user_message_last_time_sent umlts
            SET last_time_sent_ts_bigint = extract(epoch from current_timestamp)::bigint*1000
            FROM pairs p
            WHERE p.login_id = umlts.login_id AND p.message_id = umlts.message_id
            RETURNING p.*
        )
        INSERT INTO user_message_last_time_sent (login_id, message_id, last_time_sent_ts_bigint)
        SELECT p.login_id, p.message_id, extract(epoch from current_timestamp)::bigint*1000
        FROM pairs p
        WHERE NOT EXISTS (SELECT 1 FROM upsert u WHERE u.login_id = p.login_id AND u.message_id = p.message_id);

END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

drop_func_update_user_message_last_time_sent = """DROP FUNCTION IF EXISTS "update_user_message_last_time_sent" (hstore[])"""

func_get_and_update_messages_to_send = """
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

drop_func_get_and_update_messages_to_send = """DROP FUNCTION IF EXISTS "get_and_update_messages_to_send" (hstore[])"""

func_get_localized_message = """
CREATE OR REPLACE FUNCTION "get_localized_message" (
    p_login_id int8,
    p_message_id int4
)
RETURNS SETOF "public"."message_localization" AS
$body$

DECLARE
    v_language_id int2;
    v_has_localization bool;

BEGIN

    SELECT INTO v_language_id
        l.language_id
    FROM login l
    WHERE l.id = p_login_id;

    SELECT INTO v_has_localization
        COUNT(*) = 1
    FROM message_localization m
    WHERE m.message_id = p_message_id
        AND m.language_id = v_language_id;

    RETURN QUERY SELECT
        ml.*
    FROM message_localization ml
    WHERE v_language_id IS NOT NULL
        AND ml.message_id = p_message_id
        AND ml.language_id = CASE WHEN v_has_localization THEN v_language_id ELSE 1 END;

END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

drop_func_get_localized_message = """DROP FUNCTION IF EXISTS "get_localized_message" (int8, int4)"""

func_add_message = """
CREATE OR REPLACE FUNCTION "add_message" (
    p_message_name text,
    p_trigger_event_id int4,
    p_cooldown_ts int8,
    p_language_id int2,
    p_message_title text,
    p_message_text text,
    p_screen text
)
RETURNS int4 AS
$body$

DECLARE
    v_message_exists bool;
    v_message_id int4;

BEGIN

    SELECT INTO v_message_exists
        COUNT(*) > 0
    FROM message m
    WHERE m.name = p_message_name;

    IF NOT v_message_exists
    THEN
        INSERT INTO message(name, trigger_event_id, cooldown_ts, screen)
        VALUES (p_message_name, p_trigger_event_id, p_cooldown_ts, p_screen);
    END IF;

    SELECT INTO v_message_id
        m.id
    FROM message m
    WHERE m.name = p_message_name;

    INSERT INTO message_localization(message_id, language_id, message_title, message_text)
    VALUES (v_message_id, p_language_id, p_message_title, p_message_text);

    RETURN v_message_id;

END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

drop_func_add_message = """DROP FUNCTION IF EXISTS "add_message" (text, int4, int8, int2, text, text, text)"""

def upgrade():
    context = op.get_context()
    connection = op.get_bind()

    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO public;")

    if not context.dialect.has_table(connection.engine, 'login'):
        op.create_table('login',
            sa.Column('id', sa.BigInteger(), server_default=sa.text(u"NULL::BIGINT"), nullable=False),
            sa.Column('language_id', sa.SmallInteger(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

    if not context.dialect.has_table(connection.engine, 'message'):
        op.create_table('message',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('cooldown_ts', sa.BigInteger(), nullable=True),
            sa.Column('trigger_event_id', sa.Integer(), nullable=True),
            sa.Column('screen', sa.Text(), server_default=sa.text(u"''::text"), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name', name="c_message_unique_name")
        )

    if not context.dialect.has_table(connection.engine, 'device'):
        op.create_table('device',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('login_id', sa.BigInteger(), nullable=False),
            sa.Column('platform_id', sa.SmallInteger(), nullable=False),
            sa.Column('device_id', sa.Text(), nullable=False),
            sa.Column('device_token', sa.Text(), nullable=False),
            sa.Column('device_token_new', sa.Text(), nullable=True),
            sa.Column('application_version', sa.Integer(), nullable=True),
            sa.Column('unregistered_ts', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['login_id'], ['login.id'], ondelete='CASCADE', name="Ref_device_to_login"),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('login_id', 'platform_id', 'device_id', name="c_device_unique_user_device")
        )
        op.create_index(op.f('idx_device_login_id'), 'device', ['login_id'], unique=False)

    if not context.dialect.has_table(connection.engine, 'message_localization'):
        op.create_table('message_localization',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('message_id', sa.Integer(), nullable=False),
            sa.Column('language_id', sa.SmallInteger(), nullable=False),
            sa.Column('message_title', sa.Text(), nullable=False),
            sa.Column('message_text', sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(['message_id'], ['message.id'], ondelete='CASCADE', name="ref_message_id_to_message"),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('message_id', 'language_id', name="c_message_loc_unique_message_language")
        )

    if not context.dialect.has_table(connection.engine, 'user_message_last_time_sent'):
        op.create_table('user_message_last_time_sent',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('login_id', sa.BigInteger(), nullable=False),
            sa.Column('message_id', sa.Integer(), nullable=False),
            sa.Column('last_time_sent_ts_bigint', sa.BigInteger(), nullable=False),
            sa.ForeignKeyConstraint(['login_id'], ['login.id'], ondelete='CASCADE', name="ref_login_id_to_login"),
            sa.ForeignKeyConstraint(['message_id'], ['message.id'], ondelete='CASCADE', name="ref_message_id_to_message"),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('login_id', 'message_id', name="c_user_unique_message")
        )

    op.execute(func_process_user_login)
    op.execute(func_get_elligible_user_message_pairs)
    op.execute(func_update_user_message_last_time_sent)
    op.execute(func_get_and_update_messages_to_send)
    op.execute(func_get_localized_message)
    op.execute(func_add_message)


def downgrade():
    op.execute(drop_func_process_user_login)
    op.execute(drop_func_get_elligible_user_message_pairs)
    op.execute(drop_func_update_user_message_last_time_sent)
    op.execute(drop_func_get_and_update_messages_to_send)
    op.execute(drop_func_get_localized_message)
    op.execute(drop_func_add_message)
    op.drop_table('user_message_last_time_sent')
    op.drop_table('message_localization')
    op.drop_index(op.f('idx_device_login_id'), table_name='device')
    op.drop_table('device')
    op.drop_table('message')
    op.drop_table('login')
