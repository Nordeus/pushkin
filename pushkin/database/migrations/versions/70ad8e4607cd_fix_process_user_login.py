"""fix process_user_login

Revision ID: 70ad8e4607cd
Revises: 822b8de2c260
Create Date: 2016-08-02 15:13:08.896451

"""

# revision identifiers, used by Alembic.
revision = '70ad8e4607cd'
down_revision = '822b8de2c260'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

func_process_user_login_new="""
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

func_process_user_login_old = """
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
		UPDATE device
		SET application_version = d.application_version
		FROM data d
		WHERE device.device_token = d.device_token
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

def upgrade():
    op.execute(func_process_user_login_new)
    op.execute("UPDATE device SET unregistered_ts = NULL;")


def downgrade():
    op.execute(func_process_user_login_old)
