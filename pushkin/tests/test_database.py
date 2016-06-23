'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import pytest
from pushkin.database import database
import datetime, time
from pushkin import context

from pushkin import test_config_ini_path
context.setup_configuration(test_config_ini_path)

@pytest.fixture
def setup_database():
    database.init_db()
    database.create_database()



def test_devices(setup_database):
    database.process_user_login(login_id=12345, language_id=7, platform_id=1, device_token='123', application_version=1007)
    assert list(database.get_device_tokens(login_id=12345)) == [(1, '123')]
    database.process_user_login(login_id=12345, language_id=7, platform_id=1, device_token='124', application_version=1007)
    database.process_user_login(login_id=12345, language_id=7, platform_id=1, device_token='125', application_version=1007)
    assert list(database.get_device_tokens(login_id=12345)) == [(1, '123'), (1, '124'), (1, '125')]


def test_message(setup_database):
    # user using serbian language
    database.process_user_login(login_id=12345, language_id=7, platform_id=1, device_token='123',
                                application_version=1007)

    # message with english only translation
    message_1 = database.add_message(message_name='test', language_id=1, message_title='title en',
                                      message_text='text en')
    assert message_1.message_id == 1
    localized_message = database.get_localized_message(login_id=12345, message_id=message_1.message_id)
    assert localized_message.message_title == 'title en'
    assert localized_message.message_text == 'text en'
    assert localized_message.language_id == 1
    assert localized_message.message.screen == ''

    # adding other translation different from serbian
    message_2 = database.add_message(message_name='test', language_id=0, message_title='title other',
                                      message_text='text other')
    localized_message = database.get_localized_message(login_id=12345, message_id=message_2.message_id)
    assert localized_message.message_title == 'title en'
    assert localized_message.message_text == 'text en'
    assert localized_message.language_id == 1
    assert localized_message.message.screen == ''

    # adding serbian translation
    message_3 = database.add_message(message_name='test', language_id=7, message_title='title sr',
                                      message_text='text sr')
    localized_message = database.get_localized_message(login_id=12345, message_id=message_3.message_id)
    assert localized_message.message_title == 'title sr'
    assert localized_message.message_text == 'text sr'
    assert localized_message.language_id == 7
    assert localized_message.message.screen == ''

    # message with no english neither serbian translation
    bad_message = database.add_message(message_name='test_bad', language_id=0, message_title='title bad',
                                      message_text='text bad')
    localized_message = database.get_localized_message(login_id=12345, message_id=bad_message.message_id)
    assert localized_message is None

    # user doesn't exist
    localized_message = database.get_localized_message(login_id=12346, message_id=message_3.message_id)
    assert localized_message is None

    # delete a message
    database.delete_message(message_1.message)
    assert database.get_message('test') is None

def test_message_blacklist(setup_database):
    login = database.upsert_login(12345, 7)
    blacklist = database.upsert_message_blacklist(12345, [7])
    reloaded_blacklists = database.get_all_message_blacklist()
    assert len(reloaded_blacklists) == 1

    assert reloaded_blacklists[0].login_id == blacklist.login_id
    assert reloaded_blacklists[0].blacklist == blacklist.blacklist

def test_user(setup_database):
    login = database.upsert_login(12345, 7)
    reloaded_login = database.get_login(12345)
    assert login.id == reloaded_login.id
    assert login.language_id == reloaded_login.language_id


    device = database.upsert_device(login_id=login.id, platform_id=1, device_token='123',
                                    application_version=1001, unregistered_ts=datetime.datetime.now())
    reloaded_devices = database.get_devices(login)
    assert device.id == reloaded_devices[0].id
    assert device.login_id == reloaded_devices[0].login_id
    assert device.platform_id == reloaded_devices[0].platform_id
    assert device.device_token == reloaded_devices[0].device_token

    database.delete_device(device)
    assert len(database.get_devices(login)) == 0

    database.delete_login(login)
    assert database.get_login(12345) is None

def test_unregistered_device(setup_database):
    login = database.upsert_login(12345, 7)
    device = database.upsert_device(login_id=login.id, platform_id=1, device_token='123', application_version=1001)
    assert len(database.get_device_tokens(12345)) == 1

    database.update_unregistered_devices([{'login_id': device.login_id, 'device_token': device.device_token}])
    assert len(database.get_device_tokens(12345)) == 0

def test_canonical(setup_database):
    login = database.upsert_login(12345, 7)
    old_token = '123'
    new_token = '124'
    database.upsert_device(login_id=login.id, platform_id=1, device_token=old_token, application_version=1001)
    canonical_data = [{'login_id': login.id, 'old_token': old_token, 'new_token': new_token}]
    database.update_canonicals(canonical_data)
    assert list(database.get_device_tokens(login_id=login.id)) == [(1, new_token)]

def test_device_overflow(setup_database):
    login_id = 12345
    database.process_user_login(login_id=login_id, language_id=7, platform_id=1, device_token='123', application_version=1007)
    assert list(database.get_device_tokens(login_id=login_id)) == [(1, '123')]
    database.update_canonicals([{'login_id': login_id, 'old_token': '123', 'new_token': '124'}])
    assert list(database.get_device_tokens(login_id=login_id)) == [(1, '124')]
    database.process_user_login(login_id=login_id, language_id=7, platform_id=1, device_token='125', application_version=1007)
    assert list(database.get_device_tokens(login_id=login_id)) == [(1, '124'), (1, '125')]
    database.process_user_login(login_id=login_id, language_id=7, platform_id=1, device_token='126', application_version=1007)
    assert list(database.get_device_tokens(login_id=login_id)) == [(1, '124'), (1, '125'), (1, '126')]
    database.process_user_login(login_id=login_id, language_id=7, platform_id=1, device_token='127', application_version=1007)
    assert list(database.get_device_tokens(login_id=login_id)) == [(1, '125'), (1, '126'), (1, '127')]
    database.update_unregistered_devices([{'login_id': login_id, 'device_token': '126'}])
    assert list(database.get_device_tokens(login_id=login_id)) == [(1, '125'), (1, '127')]
    database.process_user_login(login_id=login_id, language_id=7, platform_id=1, device_token='128', application_version=1007)
    assert list(database.get_device_tokens(login_id=login_id)) == [(1, '125'), (1, '127'), (1, '128')]
    database.process_user_login(login_id=login_id, language_id=7, platform_id=1, device_token='129', application_version=1007)
    assert list(database.get_device_tokens(login_id=login_id)) == [(1, '127'), (1, '128'), (1, '129')]


def test_ttl(setup_database):
    user_id = 12345
    event_ts_bigint = int(round(time.time() * 1000))
    expiry_millis = 60000
    login = database.upsert_login(user_id, 1)
    device = database.upsert_device(login_id=login.id, platform_id=1, device_token='123', application_version=1001)
    localized_message = database.add_message(message_name='test', language_id=1, message_title='title en',
                                      message_text='text en', expiry_millis=expiry_millis)
    raw_messages = database.get_raw_messages(
                                login_id=user_id, title=localized_message.message_title,
                                content=localized_message.message_text.format,
                                screen=localized_message.message.screen, game='game', world_id=1,
                                dry_run=True, message_id=localized_message.message_id, event_ts_bigint=event_ts_bigint,
                                expiry_millis=localized_message.message.expiry_millis
    )
    assert raw_messages[0]['time_to_live_ts_bigint'] == event_ts_bigint + expiry_millis

