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
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import create_engine, func, text, update, bindparam, and_

import psycopg2 as dbapi2
import psycopg2.extras

"""Module containing database wrapper calls."""

ENGINE=None
SESSION=None

def init_db():
    global ENGINE
    global SESSION
    if ENGINE is None:
        ENGINE = create_engine('postgresql+psycopg2://{db_user}:{db_pass}@localhost:5432/{db_name}'.format(
            db_user=config.db_user, db_pass=config.db_pass, db_name=config.db_name))

def create_database():
    """Create database by executing db_create.sql"""
    close_session()
    db_create_sql_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db_create.sql')
    with open(db_create_sql_path, 'r') as fd:
        sql_create_commands = fd.read()
        ENGINE.execute(sql_create_commands)

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
    with dbapi2.connect('postgresql://{db_user}:{db_pass}@localhost:5432/{db_name}'.format(db_user=config.db_user, db_pass=config.db_pass, db_name=config.db_name)) as conn:
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
        Session = sessionmaker(bind=ENGINE)
        SESSION = Session()
    return SESSION

def close_session():
    '''
    Close SQLAlchemy session.
    '''
    global SESSION
    if SESSION is not None:
        SESSION.close()


def get_device_tokens(login_id):
    '''
    Get device tokens for a given login.
    '''
    session = get_session()
    return session.query(model.Device.platform_id,
                  func.coalesce(model.Device.device_token_new, model.Device.device_token).label('device_token')).\
        filter(model.Device.login_id == login_id).filter(model.Device.unregistered_ts.is_(None))


def get_raw_messages(login_id, title, content, screen, game, world_id, dry_run, message_id=0):
    '''
    Get message dictionaries for a login id and message params.
    '''
    raw_messages = []
    base_notification = {
        'login_id': login_id,
        'title': title.decode('utf-8'),
        'content': content.decode('utf-8'),
        'game': game,
        'world_id': world_id,
        'screen': screen,
        'time': int(round(time.time() * 1000)),
        'time_to_live_ts_bigint': int(round(time.time() * 1000)) + constants.TIME_TO_LIVE_HOURS * 60 * 60 * 1000,
        'status': constants.NOTIFICATION_READY,
        'message_id': message_id,
        'campaign_id': 0,
        'sending_id': 0,
        'dry_run': dry_run
    }
    for platform_id, device_token in get_device_tokens(login_id):
        notification = base_notification.copy()
        notification['receiver_id'] = device_token
        notification['platform'] = platform_id
        raw_messages.append(notification)
    return raw_messages


def update_canonicals(canonicals):
    '''
    Update cannonical data for android devices.
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
    '''
    global ENGINE
    binding = [{"p_{}".format(k): v for k, v in u.items()} for u in unregistered]
    device_table = model.metadata.tables['device']
    stmt = update(device_table).\
        values(unregistered_ts=func.now()).\
        where(and_(device_table.c.login_id == bindparam('p_login_id'),
                   func.coalesce(device_table.c.device_token_new, device_table.c.device_token) == bindparam('p_device_token')))
    ENGINE.execute(stmt, binding)

def process_user_login(login_id, language_id, platform_id, device_id, device_token, application_version):
    '''
    Add or update device and login data.
    '''
    session = get_session()
    session.execute(text('SELECT process_user_login(:login_id, (:language_id)::int2, (:platform_id)::int2, :device_id, :device_token, :application_version)'),
                    {
                    'login_id': login_id,
                    'language_id': language_id,
                    'platform_id': platform_id,
                    'device_id': device_id,
                    'device_token': device_token,
                    'application_version': application_version,
                    })
    session.commit()

def upsert_login(login_id, language_id):
    '''
    Add or update a login entity.
    '''
    session = get_session()
    login = session.query(model.Login).filter(model.Login.id == login_id).one_or_none()
    if login is not None:
        login.language_id = language_id
    else:
        login = model.Login(id=login_id, language_id=language_id)
        session.add(login)
    session.commit()
    return login

def upsert_device(login_id, platform_id, device_id, device_token, application_version, unregistered_ts=None):
    '''
    Add or update a device entity.
    '''
    session = get_session()
    login = session.query(model.Login).filter(model.Login.id == login_id).one()
    device = session.query(model.Device).\
        filter(model.Device.login == login).\
        filter(model.Device.platform_id == platform_id).\
        filter(model.Device.device_id == device_id).\
        one_or_none()
    if device is not None:
        device.device_token = device_token
        device.application_version = application_version
        device.unregistered_ts = unregistered_ts
        device.device_token_new = None
    else:
        device = model.Device(login=login, platform_id=platform_id, device_id=device_id, device_token=device_token,
                              application_version=application_version, unregistered_ts=unregistered_ts)
        session.add(device)
    session.commit()
    return device

def get_all_logins():
    '''
    Get list of all logins.
    '''
    session = get_session()
    logins = session.query(model.Login).all()
    return logins

def get_login(login_id):
    '''
    Get a specific login by id.
    '''
    session = get_session()
    login = session.query(model.Login).filter(model.Login.id == login_id).one_or_none()
    return login

def delete_login(login):
    '''
    Delete a specific login together with all devices of that user.
    '''
    session = get_session()
    for device in login.devices:
        session.delete(device)
    session.delete(login)
    session.commit()

def delete_device(device):
    '''
    Delete a specific device.
    '''
    session = get_session()
    session.delete(device)
    session.commit()

def get_localized_message(login_id, message_id):
    '''
    Get message localization for language of a specific user.

    If translation for language of a user doesn't exist English translation is given.
    '''
    session = get_session()
    localized_message = session.query(model.MessageLocalization).options(joinedload(model.MessageLocalization.message)).\
        from_statement(text("select * from get_localized_message(:login_id, :message_id)")).\
        params(login_id=login_id, message_id=message_id).first()
    return localized_message

def upsert_message(message_name, cooldown_ts, trigger_event_id, screen):
    '''
    Add or update a message.
    '''
    session = get_session()
    message = session.query(model.Message).filter(model.Message.name == message_name).one_or_none()
    if message is not None:
        message.cooldown_ts = cooldown_ts
        message.trigger_event_id = trigger_event_id
        message.screen = screen
    else:
        message = model.Message(name=message_name, cooldown_ts=cooldown_ts, trigger_event_id=trigger_event_id, screen=screen)
        session.add(message)
    session.commit()
    return message

def upsert_message_localization(message_name, language_id, message_title, message_text):
    '''
    Add or update a message localization.
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
    return message_localization

def add_message(message_name, language_id, message_title, message_text, trigger_event_id=None, cooldown_ts=None,
                screen=''):
    '''
    Add or update a message with localization for one language.
    '''
    message = upsert_message(message_name, cooldown_ts, trigger_event_id, screen)
    message_localization = upsert_message_localization(message_name, language_id, message_title, message_text)
    return message_localization

def get_all_messages():
    '''
    Get list of all messages from database.
    '''
    session = get_session()
    messages = session.query(model.Message).all()
    return messages

def get_message(message_name):
    '''
    Get a specific message.
    '''
    session = get_session()
    message = session.query(model.Message).filter(model.Message.name == message_name).one_or_none()
    return message

def delete_message(message):
    '''
    Delete a specific message with all localizations.
    '''
    session = get_session()
    for message_localization in message.localizations:
        session.delete(message_localization)
    session.delete(message)
    session.commit()

def delete_message_localization(message_localization):
    '''
    Delete a specific message localization.
    '''
    session = get_session()
    session.delete(message_localization)
    session.commit()

def get_event_to_message_mapping():
    '''
    Return a mapping of event ids to messages ids in format {event_id: [message_ids]}.
    '''
    session = get_session()
    messages_with_event = session.query(model.Message.trigger_event_id, model.Message.id).filter(model.Message.trigger_event_id.isnot(None)).all()
    mapping = defaultdict(list)
    for trigger_event_id, id in messages_with_event:
        mapping[trigger_event_id].append(id)
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
    with dbapi2.connect('postgresql://{db_user}:{db_pass}@localhost:5432/{db_name}'.format(db_user=config.db_user, db_pass=config.db_pass, db_name=config.db_name)) as conn:
        psycopg2.extras.register_hstore(conn)
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query)
            user_message_pairs = cur.fetchall()[0][0]
    return user_message_pairs
