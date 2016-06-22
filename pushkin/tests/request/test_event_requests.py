'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import pytest
from pushkin.request.requests import EventRequestSingle
from pushkin.protobuf import EventMessage_pb2
from pushkin.request.requests import EventRequestBatch
from pushkin.request.event_handlers import EventHandlerManager
from pushkin import context

from pushkin import config
from pushkin.database import database
from pushkin import test_config_ini_path

context.setup_configuration(test_config_ini_path)
database.init_db()

@pytest.fixture
def mock_log(mocker):
    mocker.patch("pushkin.context.main_logger")


@pytest.fixture
def setup(mock_log):
    '''
    Runs setup before and clean up after a test which use this fixture
    '''
    # prepare database for test
    database.create_database()
    prepare_demodata()


def prepare_demodata():
    # add some test users
    database.process_user_login(login_id=1, language_id=1, platform_id=2, device_token='dtoken1', application_version=200)
    database.process_user_login(login_id=2, language_id=1, platform_id=2, device_token='dtoken2', application_version=200)
    database.process_user_login(login_id=3, language_id=1, platform_id=2, device_token='dtoken3', application_version=200)

    # insert messages
    database.add_message('msg1', 1, 'title', 'text', 1)
    database.add_message('msg2', 1, 'title', 'text', 1)
    database.add_message('msg3', 1, 'title', 'text', 2)
    database.add_message('msg4', 1, 'title {title_param}', 'text {text_param}', 3)


def create_batch_with_login_event(user_id, platform_id, device_token):
    event_proto = EventMessage_pb2.Event()
    # add required parameters
    pair = event_proto.pairs.add()
    pair.key = 'platformId'
    pair.value = str(platform_id)
    pair = event_proto.pairs.add()
    pair.key = 'deviceToken'
    pair.value = device_token
    pair = event_proto.pairs.add()
    pair.key = 'applicationVersion'
    pair.value = '1'
    params = dict((pair.key, pair.value) for pair in event_proto.pairs)
    event = EventRequestSingle(user_id, config.login_event_id, params, 1442502890000)
    return event


def test_login_event_persists_user_data(setup):
    '''Test that user data is persisted after login event is received'''
    context.event_handler_manager = EventHandlerManager()
    event_batch = create_batch_with_login_event(user_id=1338, platform_id=2, device_token='str_device_token')
    event_request = EventRequestBatch([event_batch])
    event_request.process()
    device_tokens = list(database.get_device_tokens(1338))
    assert device_tokens == [(2, 'str_device_token')]


def test_login_event_duplicate(setup):
    '''Tests that user data is persisted correctly for duplicated login events'''
    context.event_handler_manager = EventHandlerManager()
    event_batch = create_batch_with_login_event(user_id=1338, platform_id=1, device_token='str_device_token_1')
    event_request_platform1 = EventRequestBatch([event_batch])
    event_request_platform1.process()
    event_request_platform1.process()

    device_tokens = list(database.get_device_tokens(1338))
    assert device_tokens == [(1, 'str_device_token_1')]


def test_login_event_more_platforms(setup):
    '''Tests that user data is persisted for more platforms'''
    context.event_handler_manager = EventHandlerManager()
    event_batch_platform1 = create_batch_with_login_event(user_id=1338, platform_id=1, device_token='str_device_token_1')
    event_request_platform1 = EventRequestBatch([event_batch_platform1])
    event_request_platform1.process()

    event_batch_platform2 = create_batch_with_login_event(user_id=1338, platform_id=2, device_token='str_device_token_2')
    event_request_platform2 = EventRequestBatch([event_batch_platform2])
    event_request_platform2.process()

    device_tokens = list(database.get_device_tokens(1338))
    assert device_tokens == [(1, 'str_device_token_1'), (2, 'str_device_token_2')]


def test_login_event_same_platform_different_device(setup):
    '''Tests that both devices are persisted if they have different tokens'''
    context.event_handler_manager = EventHandlerManager()
    event_batch_platform1 = create_batch_with_login_event(user_id=1338, platform_id=1, device_token='str_device_token_1')
    event_request_platform1 = EventRequestBatch([event_batch_platform1])
    event_request_platform1.process()

    event_batch_platform2 = create_batch_with_login_event(user_id=1338, platform_id=1, device_token='str_device_token_2')
    event_request_platform2 = EventRequestBatch([event_batch_platform2])
    event_request_platform2.process()

    device_tokens = list(database.get_device_tokens(1338))
    assert device_tokens == [(1, 'str_device_token_1'), (1, 'str_device_token_2')]


def test_build_messages_missing_user(setup):
    context.event_handler_manager = EventHandlerManager()
    event_proto = EventMessage_pb2.Event()
    event_proto.user_id = 5
    event_proto.event_id = 1
    event_proto.event_type = 2
    event_proto.timestamp = 1442502890000
    request = EventRequestBatch([event_proto])
    assert len(request.build_messages()) == 0


def test_build_messages_missing_event(setup):
    context.event_handler_manager = EventHandlerManager()
    event_proto = EventMessage_pb2.Event()
    event_proto.user_id = 1
    event_proto.event_id = 5
    event_proto.event_type = 2
    event_proto.timestamp = 1442502890000
    request = EventRequestBatch([event_proto])
    assert len(request.build_messages()) == 0


def test_build_messages_single_event_msg(setup):
    context.event_handler_manager = EventHandlerManager()
    event_proto = EventMessage_pb2.Event()
    event_proto.user_id = 1
    event_proto.event_id = 2
    event_proto.event_type = 2
    event_proto.timestamp = 1442502890000
    request = EventRequestBatch([event_proto])
    messages = request.build_messages()
    print messages
    assert len(messages) == 1
    assert messages[0]['message_id'] == 3


def test_build_messages_multiple_event_msg(setup):
    context.event_handler_manager = EventHandlerManager()
    event_proto = EventMessage_pb2.Event()
    event_proto.user_id = 1
    event_proto.event_id = 1
    event_proto.event_type = 2
    event_proto.timestamp = 1442502890000
    request = EventRequestBatch([event_proto])
    messages = request.build_messages()
    print messages
    assert len(messages) == 2
    assert set([message['message_id'] for message in messages]) == {1, 2}


def test_login_and_then_other_event(setup, mocker):
    '''Tests that both devices are persisted if they have different tokens'''
    context.event_handler_manager = EventHandlerManager()

    event_batch_platform1 = create_batch_with_login_event(user_id=1338, platform_id=1, device_token='str_device_token_1')
    event_request_platform1 = EventRequestBatch([event_batch_platform1])
    event_request_platform1.process()

    # test no message
    event1 = EventRequestSingle(1, -1, None, 1442502890000)
    event_request_other1 = EventRequestBatch([event1])
    messages1 = event_request_other1.build_messages()
    assert len(messages1) == 0

    # test parameter from event
    params = {'title_param': 'param title', 'text_param': 'param content'}
    event2 = EventRequestSingle(user_id=1, event_id=3, pairs=params, timestamp=2442502890000)
    event_request_other2 = EventRequestBatch([event2])
    messages2 = event_request_other2.build_messages()
    assert len(messages2) == 1
    assert messages2[0]['message_id'] == 4
    assert messages2[0]['content'] == 'text param content'
    assert messages2[0]['title'] == 'title param title'

    # test missing parameter which is required by localization
    event3 = EventRequestSingle(user_id=1, event_id=3, pairs=None, timestamp=1442502890000)
    event_request_other3 = EventRequestBatch([event3])
    messages3 = event_request_other3.build_messages()
    assert len(messages3) == 0
