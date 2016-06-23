BEGIN;

DROP TABLE IF EXISTS "alembic_version" CASCADE;
CREATE TABLE "alembic_version" (
	version_num VARCHAR(32) NOT NULL
);

DROP TABLE IF EXISTS "login" CASCADE;
CREATE TABLE "login" (
	"id" int8 NOT NULL,
	"language_id" int2,
	PRIMARY KEY ("id")
);

DROP TABLE IF EXISTS "device" CASCADE;
CREATE TABLE "device" (
	"id" serial NOT NULL,
	"login_id" int8 NOT NULL,
	"platform_id" int2 NOT NULL,
	"device_token" text NOT NULL,
	"device_token_new" text,
	"application_version" int4,
	"unregistered_ts" timestamp,
	PRIMARY KEY("id"),
	CONSTRAINT "c_device_unique_user_device" UNIQUE("login_id", "platform_id", "device_token")
);

CREATE INDEX "idx_device_login_id" ON "device" ("login_id");

ALTER TABLE "device" ADD CONSTRAINT "Ref_device_to_login" FOREIGN KEY ("login_id")
	REFERENCES "login"("id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE NO ACTION
	NOT DEFERRABLE;

DROP TABLE IF EXISTS "message" CASCADE;
CREATE TABLE "message" (
	"id" serial NOT NULL,
	"name" text NOT NULL,
	"cooldown_ts" int8,
	"trigger_event_id" int4,
	"screen" text NOT NULL DEFAULT '',
	"expiry_millis" int8,
	PRIMARY KEY ("id"),
	CONSTRAINT "c_message_unique_name" UNIQUE("name")
);

DROP TABLE IF EXISTS "message_blacklist" CASCADE;
CREATE TABLE "message_blacklist" (
    "id" serial NOT NULL,
    "login_id" int8 NOT NULL,
    "blacklist" int4[],
    PRIMARY KEY ("id")
);

DROP TABLE IF EXISTS "message_localization" CASCADE;
CREATE TABLE "message_localization" (
	"id" serial NOT NULL,
	"message_id" int4 NOT NULL,
	"language_id" int2 NOT NULL,
	"message_title" text NOT NULL,
	"message_text" text NOT NULL,
	PRIMARY KEY("id"),
	CONSTRAINT "c_message_loc_unique_message_language" UNIQUE("message_id", "language_id")
);

ALTER TABLE "message_localization" ADD CONSTRAINT "ref_message_id_to_message" FOREIGN KEY ("message_id")
	REFERENCES "message"("id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE NO ACTION
	NOT DEFERRABLE;

DROP TABLE IF EXISTS "user_message_last_time_sent" CASCADE;
CREATE TABLE "user_message_last_time_sent" (
	"id" serial NOT NULL,
	"login_id" int8 NOT NULL,
	"message_id" int4 NOT NULL,
	"last_time_sent_ts_bigint" int8 NOT NULL,
	PRIMARY KEY ("id"),
	CONSTRAINT "c_user_unique_message" UNIQUE("login_id", "message_id")
);

ALTER TABLE "user_message_last_time_sent" ADD CONSTRAINT "ref_login_id_to_login" FOREIGN KEY ("login_id")
	REFERENCES "login"("id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE NO ACTION
	NOT DEFERRABLE;

ALTER TABLE "message_blacklist" ADD CONSTRAINT "ref_message_blacklist_login_id_to_login" FOREIGN KEY ("login_id")
	REFERENCES "login"("id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE NO ACTION
	NOT DEFERRABLE;

ALTER TABLE "user_message_last_time_sent" ADD CONSTRAINT "ref_message_id_to_message" FOREIGN KEY ("message_id")
	REFERENCES "message"("id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE NO ACTION
	NOT DEFERRABLE;

DROP FUNCTION IF EXISTS "process_user_login" (int8, int2, int2, text, text, int4);
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

DROP FUNCTION IF EXISTS "get_elligible_user_message_pairs" (hstore[]);
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

DROP FUNCTION IF EXISTS "update_user_message_last_time_sent" (hstore[]);
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

DROP FUNCTION IF EXISTS "get_and_update_messages_to_send" (hstore[]);
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


DROP FUNCTION IF EXISTS "get_localized_message" (int8, int4);
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


DROP FUNCTION IF EXISTS "add_message" (text, int4, int8, int2, text, text, text);
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

END;
