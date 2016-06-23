'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import time
import os

from pushkin.sender.nordifier import constants
from pushkin import config, context
from collections import defaultdict

from pushkin.database import model
from sqlalchemy.orm import sessionmaker, contains_eager
from sqlalchemy import create_engine, func, text, update, bindparam, and_

import psycopg2 as dbapi2
import psycopg2.extras

from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
from alembic.script import ScriptDirectory as AlembicScriptDirectory
from alembic.migration import MigrationContext as AlembicMigrationContext

"""Module containing database wrapper calls."""

ENGINE = None
SESSION = None
ALEMBIC_CONFIG = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'alembic.ini')

def init_db():
    global ENGINE
    global SESSION
    if ENGINE is None:
        ENGINE = create_engine(config.sqlalchemy_url, pool_size=config.db_pool_size, max_overflow=0)

def create_database():
    """Create database by executing db_create.sql"""
    db_create_sql_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db_create.sql')
    with open(db_create_sql_path, 'r') as fd:
        sql_create_commands = fd.read()
        ENGINE.execute(sql_create_commands)
        ENGINE.execute(text("INSERT INTO alembic_version VALUES (:version_num)"), {"version_num": get_head_revision()})

def upgrade_database():
    alembic_cfg = AlembicConfig(ALEMBIC_CONFIG)
    alembic_command.upgrade(alembic_cfg, "head")

def get_head_revision():
    alembic_cfg = AlembicConfig(ALEMBIC_CONFIG)
    script = AlembicScriptDirectory.from_config(alembic_cfg)
    head_revision = script.get_current_head()
    return head_revision

def get_current_revision():
    alembic_context = AlembicMigrationContext.configure(ENGINE.connect())
    current_revision = alembic_context.get_current_revision()
    return current_revision

def execute_query(query):
    '''
    Execute a specific query.
    '''
    with dbapi2.connect(database=config.db_name, user=config.db_user) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query)

def execute_query_with_results(query):
    '''
    Execute a specific query and return results.
    '''
    with dbapi2.connect('host=localhost user={db_user} password={db_pass} port=5432 dbname={db_name}'.format(db_user=config.db_user, db_pass=config.db_pass, db_name=config.db_name)) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query)
            rows = cur.fetchall()
    return rows

def get_session():
    '''
    Get SQLAlchemy session.
    '''
    global ENGINE
    global SESSION
    if SESSION is None:
        SESSION = sessionmaker(bind=ENGINE)
    session = SESSION()
    return session


def get_device_tokens(login_id):
    '''
    Get device tokens for a given login.
    '''
    session = get_session()
    result = session.query(model.Device.platform_id,
                    func.coalesce(model.Device.device_token_new, model.Device.device_token).label('device_token')).\
        filter(model.Device.login_id == login_id).filter(model.Device.unregistered_ts.is_(None)).all()
    session.close()
    return result


def get_raw_messages(login_id, title, content, screen, game, world_id, dry_run, message_id=0, event_ts_bigint=None,
                     expiry_millis=None):
    '''
    Get message dictionaries for a login id and message params.
    '''
    if expiry_millis is not None and event_ts_bigint is not None:
        time_to_live_ts_bigint = event_ts_bigint + expiry_millis
    else:
        time_to_live_ts_bigint = int(round(time.time() * 1000)) + constants.TIME_TO_LIVE_HOURS * 60 * 60 * 1000
    raw_messages = []
    base_notification = {
        'login_id': login_id,
        'title': title,
        'content': content,
        'game': game,
        'world_id': world_id,
        'screen': screen,
        'time': int(round(time.time() * 1000)),
        'time_to_live_ts_bigint': time_to_live_ts_bigint,
        'status': constants.NOTIFICATION_READY,
        'message_id': message_id,
        'campaign_id': 0,
        'sending_id': 0,
        'dry_run': dry_run
    }
    devices = get_device_tokens(login_id)
    if len(devices) > 0:
        for platform_id, device_token in devices:
            notification = base_notification.copy()
            notification['receiver_id'] = device_token
            notification['platform'] = platform_id
            raw_messages.append(notification)
    else:
        context.main_logger.debug("User with login_id={login_id} doesn't have any device.".format(login_id=login_id))
    return raw_messages


def update_canonicals(canonicals):
    '''
    Update canonical data for android devices.
    '''
    global ENGINE
    binding = [{"p_{}".format(k): v for k, v in canonical.items()} for canonical in canonicals]
    device_table = model.metadata.tables['device']
    stmt = update(device_table).\
        values(device_token_new=bindparam('p_new_token')).\
        where(and_(device_table.c.login_id == bindparam('p_login_id'),
                   func.coalesce(device_table.c.device_token_new, device_table.c.device_token) == bindparam('p_old_token')))
    ENGINE.execute(stmt, binding)

def update_unregistered_devices(unregistered):
    '''
    Update data for unregistered Android devices.

    Unregistered device will not receive notifications and will be deleted when number of devices exceeds maximum.
    '''
    global ENGINE
    binding = [{"p_{}".format(k): v for k, v in u.items()} for u in unregistered]
    device_table = model.metadata.tables['device']
    stmt = update(device_table).\
        values(unregistered_ts=func.now()).\
        where(and_(device_table.c.login_id == bindparam('p_login_id'),
                   func.coalesce(device_table.c.device_token_new, device_table.c.device_token) == bindparam('p_device_token')))
    ENGINE.execute(stmt, binding)

def process_user_login(login_id, language_id, platform_id, device_token, application_version):
    '''
    Add or update device and login data. Also deletes oldest device if number of devices exceeds maximum.
    '''
    session = get_session()
    session.execute(text('SELECT process_user_login(:login_id, (:language_id)::int2, (:platform_id)::int2,:device_token, :application_version, (:max_devices_per_user)::int2)'),
                    {
                    'login_id': login_id,
                    'language_id': language_id,
                    'platform_id': platform_id,
                    'device_token': device_token,
                    'application_version': application_version,
                    'max_devices_per_user': config.max_devices_per_user,
                    })
    session.commit()
    session.close()

def upsert_login(login_id, language_id):
    '''
    Add or update a login entity. Returns new or updated login.
    '''
    session = get_session()
    login = session.query(model.Login).filter(model.Login.id == login_id).one_or_none()
    if login is not None:
        login.language_id = language_id
    else:
        login = model.Login(id=login_id, language_id=language_id)
        session.add(login)
    session.commit()
    session.refresh(login)
    session.close()
    return login

def upsert_device(login_id, platform_id, device_token, application_version, unregistered_ts=None):
    '''
    Add or update a device entity. Returns new or updated device with relation to login preloaded.
    '''
    session = get_session()
    login = session.query(model.Login).filter(model.Login.id == login_id).one()
    device = session.query(model.Device).\
        filter(model.Device.login == login).\
        filter(model.Device.platform_id == platform_id).\
        filter(func.coalesce(model.Device.device_token_new, model.Device.device_token) == device_token).\
        one_or_none()
    if device is not None:
        device.application_version = application_version
        device.unregistered_ts = unregistered_ts
    else:
        device = model.Device(login=login, platform_id=platform_id, device_token=device_token,
                              application_version=application_version, unregistered_ts=unregistered_ts)
        session.add(device)
    session.commit()
    session.refresh(device)
    session.refresh(device.login)
    session.close()
    return device

def get_all_logins():
    '''
    Get list of all logins.
    '''
    session = get_session()
    logins = session.query(model.Login).all()
    session.close()
    return logins

def get_all_message_blacklist():
    '''
    Get list of all message blacklists
    '''
    session = get_session()
    blacklists = session.query(model.MessageBlacklist).all()
    session.close()
    return blacklists

def upsert_message_blacklist(login_id, blacklist):
    '''
    Add or update a message. Returns new or updated message.
    '''
    session = get_session()
    entity = session.query(model.MessageBlacklist).filter(model.MessageBlacklist.login_id == login_id).one_or_none()
    if entity is not None:
        entity.blacklist = blacklist
    else:
        entity = model.MessageBlacklist(login_id=login_id, blacklist=blacklist)
        session.add(entity)
    session.commit()
    session.refresh(entity)
    session.close()
    return entity

def get_login(login_id):
    '''
    Get a specific login by id.
    '''
    session = get_session()
    login = session.query(model.Login).filter(model.Login.id == login_id).one_or_none()
    session.close()
    return login

def get_devices(login):
    '''
    Get devices of a specific login.
    '''
    session = get_session()
    reloaded_login = session.query(model.Login).filter(model.Login.id == login.id).one()
    devices = reloaded_login.devices
    session.close()
    return devices

def delete_login(login):
    '''
    Delete a specific login together with all devices of that user.
    '''
    session = get_session()
    reloaded_login = session.query(model.Login).filter(model.Login.id == login.id).one()
    for device in reloaded_login.devices:
        session.delete(device)
    session.delete(reloaded_login)
    session.commit()
    session.close()

def delete_device(device):
    '''
    Delete a specific device.
    '''
    session = get_session()
    reloaded_device = session.query(model.Device).filter(model.Device.id == device.id).one()
    session.delete(reloaded_device)
    session.commit()
    session.close()

def get_localized_message(login_id, message_id):
    '''
    Get message localization for language of a specific user.

    If translation for language of a user doesn't exist English translation is given.
    '''
    session = get_session()
    localized_message = session.query(model.MessageLocalization).\
        from_statement(text("select lm.*, m.* from get_localized_message(:login_id, :message_id) lm inner join message m on lm.message_id = m.id")).\
        params(login_id=login_id, message_id=message_id).\
        options(contains_eager(model.MessageLocalization.message)).\
        one_or_none()
    session.close()
    return localized_message

def upsert_message(message_name, cooldown_ts, trigger_event_id, screen, expiry_millis):
    '''
    Add or update a message. Returns new or updated message.
    '''
    session = get_session()
    message = session.query(model.Message).filter(model.Message.name == message_name).one_or_none()
    if message is not None:
        message.cooldown_ts = cooldown_ts
        message.trigger_event_id = trigger_event_id
        message.screen = screen
        message.expiry_millis = expiry_millis
    else:
        message = model.Message(name=message_name, cooldown_ts=cooldown_ts, trigger_event_id=trigger_event_id,
                                screen=screen, expiry_millis=expiry_millis)
        session.add(message)
    session.commit()
    session.refresh(message)
    session.close()
    return message

def upsert_message_localization(message_name, language_id, message_title, message_text):
    '''
    Add or update a message localization. Returns new or updated localization with relation to message preloaded.
    '''
    session = get_session()
    message = session.query(model.Message).filter(model.Message.name == message_name).one()
    message_localization = session.query(model.MessageLocalization).\
        filter(model.MessageLocalization.message == message).\
        filter(model.MessageLocalization.language_id == language_id).\
        one_or_none()
    if message_localization is not None:
        message_localization.message_title = message_title
        message_localization.message_text = message_text
    else:
        message_localization = model.MessageLocalization(message=message, language_id=language_id,
                                                         message_title=message_title, message_text=message_text)
        session.add(message_localization)
    session.commit()
    session.refresh(message_localization)
    session.refresh(message_localization.message)
    session.close()
    return message_localization

def add_message(message_name, language_id, message_title, message_text, trigger_event_id=None, cooldown_ts=None,
                screen='', expiry_millis=None):
    '''
    Add or update a message with localization for one language.
    '''
    message = upsert_message(message_name, cooldown_ts, trigger_event_id, screen, expiry_millis)
    message_localization = upsert_message_localization(message_name, language_id, message_title, message_text)
    return message_localization

def get_all_messages():
    '''
    Get list of all messages from database.
    '''
    session = get_session()
    messages = session.query(model.Message).all()
    session.close()
    return messages

def get_message(message_name):
    '''
    Get a specific message.
    '''
    session = get_session()
    message = session.query(model.Message).filter(model.Message.name == message_name).one_or_none()
    session.close()
    return message

def get_message_localizations(message):
    '''
    Get all localizations for a specific message.
    '''
    session = get_session()
    reloaded_message = session.query(model.Message).filter(model.Message.id == message.id).one()
    localizations = reloaded_message.localizations
    session.close()
    return localizations


def delete_message(message):
    '''
    Delete a specific message with all localizations.
    '''
    session = get_session()
    reloaded_message = session.query(model.Message).filter(model.Message.id == message.id).one()
    for message_localization in reloaded_message.localizations:
        session.delete(message_localization)
    session.delete(reloaded_message)
    session.commit()
    session.close()

def delete_message_localization(message_localization):
    '''
    Delete a specific message localization.
    '''
    session = get_session()
    reloaded_message_localization = session.query(model.MessageLocalization).filter(model.MessageLocalization.id == message_localization.id).one()
    session.delete(reloaded_message_localization)
    session.commit()
    session.close()

def get_event_to_message_mapping():
    '''
    Return a mapping of event ids to messages ids in format {event_id: [message_ids]}.
    '''
    session = get_session()
    messages_with_event = session.query(model.Message.trigger_event_id, model.Message.id).filter(model.Message.trigger_event_id.isnot(None)).all()
    mapping = defaultdict(list)
    for trigger_event_id, id in messages_with_event:
        mapping[trigger_event_id].append(id)
    session.close()
    return mapping


def get_and_update_messages_to_send(user_message_set):
    '''
    Update last time a message id was send for a user.

    Expects a set of (login_id, message_id) tuples.
    '''
    hstore_items = ','.join(
        ["'{key}=>{value}'::hstore".format(key=entry[0], value=entry[1]) for entry in user_message_set])
    hstore_array = 'ARRAY[{}]'.format(hstore_items)
    query = 'SELECT get_and_update_messages_to_send({})'.format(hstore_array)
    with dbapi2.connect('host=localhost user={db_user} password={db_pass} port=5432 dbname={db_name}'.format(db_user=config.db_user, db_pass=config.db_pass, db_name=config.db_name)) as conn:
        psycopg2.extras.register_hstore(conn)
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query)
            user_message_pairs = cur.fetchall()[0][0]
    return user_message_pairs
