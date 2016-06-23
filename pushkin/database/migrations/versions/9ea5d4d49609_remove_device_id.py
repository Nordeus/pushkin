'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

# revision identifiers, used by Alembic.
revision = '9ea5d4d49609'
down_revision = '866d344d7b5d'
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
drop_func_process_user_login_new = """DROP FUNCTION IF EXISTS "process_user_login" (int8, int2, int2, text, int4)"""

func_process_user_login_old = """
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

drop_func_process_user_login_old = """DROP FUNCTION IF EXISTS "process_user_login" (int8, int2, int2, text, text, int4)"""

def upgrade():
    op.drop_column('device', 'device_id')
    op.execute(drop_func_process_user_login_old)
    op.execute(func_process_user_login_new)



def downgrade():
    op.add_column('device', sa.Column('device_id', sa.Text(), nullable=False))
    op.execute(drop_func_process_user_login_new)
    op.execute(func_process_user_login_old)
