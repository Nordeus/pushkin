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
from pushkin.request.event_handlers import EventHandler, LoginEventHandler
from pushkin import config
from pushkin import context
from pushkin import test_config_ini_path


context.setup_configuration(test_config_ini_path)

@pytest.fixture
def mock_log(mocker):
    '''Mock request processor'''
    mocker.patch('pushkin.context.main_logger')


def test_valid_event_proto(mock_log, ):
    '''Test that a valid event proto is validated correctly.'''
    event = EventRequestSingle(123, 1, None, 12345)
    event_handler = EventHandler(1)
    assert event_handler.validate(event, {})


def test_event_proto_without_user_id(mock_log):
    '''Test that an event proto without user_id fails validation'''
    event = EventRequestSingle(None, 1, None, 12345)
    event_handler = EventHandler(1)
    assert not event_handler.validate(event, {})

def test_event_proto_without_timestamp(mock_log):
    '''Test that an event proto without timestamp fails validation'''
    event = EventRequestSingle(None, 1, None)
    event_handler = EventHandler(1)
    assert not event_handler.validate(event, {})


def test_valid_login_proto(mock_log):
    '''Test that a valid login proto is validated correctly.'''
    event_proto = EventMessage_pb2.Event()
    pair = event_proto.pairs.add()
    pair.key = 'platformId'
    pair.value = '1'
    pair = event_proto.pairs.add()
    pair.key = 'deviceToken'
    pair.value = '1234'
    pair = event_proto.pairs.add()
    pair.key = 'applicationVersion'
    pair.value = '1'
    params = dict((pair.key, pair.value) for pair in event_proto.pairs)
    event = EventRequestSingle(123, config.login_event_id, params, 12345)
    assert LoginEventHandler().validate(event, params)


def test_login_proto_without_platform_id(mock_log):
    '''Test that a login proto without platform id fails validation.'''
    event_proto = EventMessage_pb2.Event()
    pair = event_proto.pairs.add()
    pair.key = 'deviceToken'
    pair.value = '1234'
    pair = event_proto.pairs.add()
    pair.key = 'applicationVersion'
    pair.value = '1'
    params = dict((pair.key, pair.value) for pair in event_proto.pairs)
    event = EventRequestSingle(123, config.login_event_id, params, 12345)
    assert not LoginEventHandler().validate(event, params)


def test_login_proto_empty_platform_id(mock_log):
    '''Test that a login proto with empty platform id fails validation.'''
    event_proto = EventMessage_pb2.Event()
    pair = event_proto.pairs.add()
    pair.key = 'platformId'
    pair.value = ''
    pair = event_proto.pairs.add()
    pair.key = 'deviceToken'
    pair.value = '1234'
    pair = event_proto.pairs.add()
    pair.key = 'applicationVersion'
    pair.value = '1'
    params = dict((pair.key, pair.value) for pair in event_proto.pairs)
    event = EventRequestSingle(123, config.login_event_id, params, 12345)
    assert not LoginEventHandler().validate(event, params)


def test_login_proto_non_numeric_platform_id(mock_log):
    '''Test that a login proto with non numeric platform id fails validation.'''
    event_proto = EventMessage_pb2.Event()
    pair = event_proto.pairs.add()
    pair.key = 'platformId'
    pair.value = 'asd'
    pair = event_proto.pairs.add()
    pair.key = 'deviceToken'
    pair.value = '1234'
    pair = event_proto.pairs.add()
    pair.key = 'applicationVersion'
    pair.value = '1'
    params = dict((pair.key, pair.value) for pair in event_proto.pairs)
    event = EventRequestSingle(123, config.login_event_id, params, 12345)
    assert not LoginEventHandler().validate(event, params)


def test_login_proto_without_device_token(mock_log):
    '''Test that a login proto without device token fails validation.'''
    event_proto = EventMessage_pb2.Event()
    pair = event_proto.pairs.add()
    pair.key = 'platformId'
    pair.value = '1'
    pair = event_proto.pairs.add()
    pair.key = 'applicationVersion'
    pair.value = '1'
    params = dict((pair.key, pair.value) for pair in event_proto.pairs)
    event = EventRequestSingle(123, config.login_event_id, params, 12345)
    assert LoginEventHandler().validate(event, params)


def test_login_proto_empty_device_token(mock_log):
    '''Test that a login proto with empty device token fails validation.'''
    event_proto = EventMessage_pb2.Event()
    pair = event_proto.pairs.add()
    pair.key = 'platformId'
    pair.value = '1'
    pair = event_proto.pairs.add()
    pair.key = 'deviceToken'
    pair.value = ''
    pair = event_proto.pairs.add()
    pair.key = 'applicationVersion'
    pair.value = '1'
    params = dict((pair.key, pair.value) for pair in event_proto.pairs)
    event = EventRequestSingle(123, config.login_event_id, params, 12345)
    assert LoginEventHandler().validate(event, params)
