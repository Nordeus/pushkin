"""max_users_per_device

Revision ID: 34dd0bf00472
Revises: 8b6104b8b8c0
Create Date: 2017-03-09 16:29:37.010594

"""

# revision identifiers, used by Alembic.
revision = '34dd0bf00472'
down_revision = '8b6104b8b8c0'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

create_get_elligible_user_message_pairs = """
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

create_update_user_message_last_time_sent = """
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

create_get_and_update_messages_to_send = """
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

func_process_user_login_old = """
DROP FUNCTION IF EXISTS "process_user_login" (int8, int2, int2, text, int4, int2, int2);
CREATE OR REPLACE FUNCTION "process_user_login" (
	p_login_id int8,
	p_language_id int2,
	p_platform_id int2,
	p_device_token text,
	p_application_version int4,
	p_max_devices_per_user int2
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
	data_tmp(login_id, platform_id, device_token, application_version) AS (
		VALUES(p_login_id, p_platform_id, p_device_token, p_application_version)
	),
	data AS (
		SELECT * FROM data_tmp WHERE device_token IS NOT NULL
	),
	update_part AS (
		UPDATE device SET
		application_version = d.application_version,
		unregistered_ts = NULL
		FROM data d
		WHERE (device.device_token = d.device_token OR device.device_token_new = d.device_token)
			AND device.login_id = d.login_id
			AND device.platform_id = d.platform_id
		RETURNING d.*
	)
	INSERT INTO device(login_id, platform_id, device_token, application_version)
	SELECT d.login_id, d.platform_id, d.device_token, d.application_version
	FROM data d
	WHERE NOT EXISTS (
		SELECT 1
		FROM update_part u
		WHERE u.login_id = d.login_id
			AND u.platform_id = d.platform_id
			AND u.device_token = d.device_token);

	WITH
	devices_ordered AS (
	SELECT
		id,
		ROW_NUMBER() OVER (PARTITION BY login_id ORDER BY unregistered_ts DESC NULLS FIRST, id DESC) AS device_order
	FROM device
	WHERE login_id = p_login_id
	),
	devices_to_delete AS (
	SELECT *
	FROM devices_ordered
	WHERE device_order > p_max_devices_per_user
	)
	DELETE FROM device
	WHERE id IN (SELECT id FROM devices_to_delete);

END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

func_process_user_login_new = """
DROP FUNCTION IF EXISTS "process_user_login" (int8, int2, int2, text, int4, int2);
CREATE OR REPLACE FUNCTION "process_user_login" (
	p_login_id int8,
	p_language_id int2,
	p_platform_id int2,
	p_device_token text,
	p_application_version int4,
	p_max_devices_per_user int2,
	p_max_users_per_device int2
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
	data_tmp(login_id, platform_id, device_token, application_version) AS (
		VALUES(p_login_id, p_platform_id, p_device_token, p_application_version)
	),
	data AS (
		SELECT * FROM data_tmp WHERE device_token IS NOT NULL
	),
	update_part AS (
		UPDATE device SET
		application_version = d.application_version,
		unregistered_ts = NULL,
		last_login_ts = NOW()
		FROM data d
		WHERE (device.device_token = d.device_token OR device.device_token_new = d.device_token)
			AND device.login_id = d.login_id
			AND device.platform_id = d.platform_id
		RETURNING d.*
	)
	INSERT INTO device(login_id, platform_id, device_token, application_version)
	SELECT d.login_id, d.platform_id, d.device_token, d.application_version
	FROM data d
	WHERE NOT EXISTS (
		SELECT 1
		FROM update_part u
		WHERE u.login_id = d.login_id
			AND u.platform_id = d.platform_id
			AND u.device_token = d.device_token);

	WITH
	devices_ordered AS (
	SELECT
		id,
		ROW_NUMBER() OVER (PARTITION BY login_id ORDER BY unregistered_ts DESC NULLS FIRST, id DESC) AS device_order
	FROM device
	WHERE login_id = p_login_id
	),
	devices_to_delete AS (
	SELECT *
	FROM devices_ordered
	WHERE device_order > p_max_devices_per_user
	)
	DELETE FROM device
	WHERE id IN (SELECT id FROM devices_to_delete);

  PERFORM keep_max_users_per_device(p_platform_id, p_device_token, p_max_users_per_device);

END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

create_keep_max_users_per_device = """
CREATE OR REPLACE FUNCTION "keep_max_users_per_device" (
  p_platform_id int2,
  p_device_token text,
  p_max_users_per_device int2
)
RETURNS "pg_catalog"."void" AS
$body$
BEGIN
  WITH
	users_ordered AS (
	SELECT
		id,
		ROW_NUMBER() OVER (PARTITION BY platform_id, COALESCE(device_token_new, device_token)
		  ORDER BY last_login_ts DESC NULLS LAST, id DESC) AS user_order
	FROM device
	WHERE platform_id = p_platform_id
	AND p_device_token = COALESCE(device_token_new, device_token)
	AND unregistered_ts	IS NULL
	),
	users_to_delete AS (
	SELECT *
	FROM users_ordered
	WHERE user_order > p_max_users_per_device
	)
	DELETE FROM device
	WHERE id IN (SELECT id FROM users_to_delete);
END;
$body$
LANGUAGE 'plpgsql'
VOLATILE
CALLED ON NULL INPUT
SECURITY INVOKER;
"""

def upgrade():
    op.execute('CREATE INDEX "idx_device_current_device_token" ON "device" USING btree (COALESCE(device_token_new, device_token));')
    op.add_column('device', sa.Column('last_login_ts', sa.DateTime, nullable=False,
                                      server_default=sa.func.current_timestamp()))

    op.execute(func_process_user_login_new)
    op.execute('DROP FUNCTION IF EXISTS "get_elligible_user_message_pairs" (hstore[]);')
    op.execute('DROP FUNCTION IF EXISTS "update_user_message_last_time_sent" (hstore[]);')
    op.execute('DROP FUNCTION IF EXISTS "get_and_update_messages_to_send" (hstore[]);')

    op.execute(create_keep_max_users_per_device)

def downgrade():
    op.drop_index(op.f('idx_device_current_device_token'), table_name='device')
    op.drop_column('device', 'last_login_ts')

    op.execute(func_process_user_login_old)
    op.execute(create_get_elligible_user_message_pairs)
    op.execute(create_update_user_message_last_time_sent)
    op.execute(create_get_and_update_messages_to_send)

    op.execute('DROP FUNCTION IF EXISTS "keep_max_users_per_device" (int2, text, int2);')
