'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import pytest
from pushkin.database import database
import time
from pushkin import context
from pushkin import test_config_ini_path

context.setup_configuration(test_config_ini_path)

@pytest.fixture
def mock_log(mocker):
    mocker.patch("pushkin.context.main_logger")


@pytest.fixture
def setup(mock_log):
    '''
    Runs setup before and clean up after a test which use this fixture
    '''
    # prepare database for test
    database.init_db()
    database.create_database()
    prepare_demodata()


def prepare_demodata():
    # add some test users
    database.process_user_login(login_id=1, language_id=1, platform_id=2, device_token='dtoken1', application_version=200)
    database.process_user_login(login_id=2, language_id=1, platform_id=2, device_token='dtoken2', application_version=200)
    database.process_user_login(login_id=3, language_id=1, platform_id=2, device_token='dtoken3', application_version=200)

    # insert messages with and without cooldown
    database.add_message(message_name='no_cooldown', language_id=1, message_title='title en', message_text='text en', trigger_event_id=1)
    database.add_message(message_name='cooldown_slow', language_id=1, message_title='title en', message_text='text en', cooldown_ts=10000)
    database.add_message(message_name='cooldown_fast', language_id=1, message_title='title en', message_text='text en', cooldown_ts=1, trigger_event_id=1)


def assert_db_consistent(dict):
    """Checks if given data is consistent with database"""
    query = "SELECT * FROM user_message_last_time_sent ORDER BY login_id, message_id"
    db_results = database.execute_query_with_results(query)
    db_dict = [{str(row[1]): str(row[2])} for row in db_results]
    assert len(db_dict) == len(dict)
    for row in db_dict:
        assert row in dict

    return db_results


def test_empty_table_one_user_no_cooldown(setup):
    """Send a message with no cooldown for the first time."""
    user_set = {(1, 1)}
    result = sorted(database.get_and_update_messages_to_send(user_set), key=lambda x: (x))
    assert result == [{'1': '1'}]
    assert_db_consistent(result)


def test_empty_table_one_user_cooldown(setup):
    """Send a message with cooldown for the first time."""
    user_set = {(1, 2)}
    result = sorted(database.get_and_update_messages_to_send(user_set), key=lambda x: (x))
    assert result == [{'1': '2'}]
    assert_db_consistent(result)


def test_empty_table_two_users(setup):
    """Send messages for 2 users for the first time."""
    user_set = {(2, 1), (3, 2)}
    result = sorted(database.get_and_update_messages_to_send(user_set), key=lambda x: (x))
    assert len(result) == 2
    for row in result:
        assert row in [{'2': '1'}, {'3': '2'}]

    assert_db_consistent(result)


def test_cooldown_updates(setup):
    """Test sending after allowed and not allowed cooldown."""
    user_set = {(1, 1), (1, 2), (2, 3)}

    result = sorted(database.get_and_update_messages_to_send(user_set), key=lambda x: (x))
    db = assert_db_consistent(result)
    timestamp_insert_no_cd = db[0][3]
    timestamp_insert_big_cd = db[1][3]
    timestamp_insert_small_cd = db[2][3]
    assert len(result) == 3
    for row in result:
        assert row in [{'1': '1'}, {'1': '2'}, {'2': '3'}]

    time.sleep(1)

    result = sorted(database.get_and_update_messages_to_send(user_set), key=lambda x: (x))
    db = assert_db_consistent([{'1': '1'}, {'1': '2'}, {'2': '3'}])
    timestamp_update_no_cd = db[0][3]
    timestamp_update_big_cd = db[1][3]
    timestamp_update_small_cd = db[2][3]

    assert timestamp_insert_no_cd < timestamp_update_no_cd
    assert timestamp_insert_big_cd == timestamp_update_big_cd
    assert timestamp_insert_small_cd < timestamp_update_small_cd

    assert len(result) == 2
    for row in result:
        assert row in [{'1': '1'}, {'2': '3'}]


def test_duplicate_pairs(setup):
    """Test if duplicates and handled."""
    user_set = {(1, 1), (1, 1)}

    result = sorted(database.get_and_update_messages_to_send(user_set), key=lambda x: (x))
    assert_db_consistent(result)
    assert result == [{'1': '1'}]
