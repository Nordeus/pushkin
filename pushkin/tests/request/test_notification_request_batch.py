'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import pytest
from pushkin.request.requests import NotificationRequestSingle
from pushkin.request.requests import NotificationRequestBatch
from pushkin.context import config
from pushkin.database import database


@pytest.fixture
def mock_log(mocker):
    mocker.patch("pushkin.context.main_logger")


def test_valid_notification_proto(mock_log):
    '''Test that a valid notification proto is validated correctly.'''
    notification = NotificationRequestSingle(1338, "Msg title", "Text of a message.", "some_screen_id")
    assert NotificationRequestBatch([notification]).validate_single(notification)


def test_notification_proto_without_login_id(mock_log):
    '''Test that a notification proto without login_id fails validation'''
    notification = NotificationRequestSingle(None, "Msg title", "Text of a message.", "some_screen_id")
    assert not NotificationRequestBatch([notification]).validate_single(notification)


def test_notification_proto_without_title(mock_log):
    '''Test that a notification proto without title fails validation'''
    notification = NotificationRequestSingle(1338, None, "Text of a message.", "some_screen_id")
    assert not NotificationRequestBatch([notification]).validate_single(notification)


def test_notification_proto_empty_title(mock_log):
    '''Test that a notification proto with empty title fails validation'''
    notification = NotificationRequestSingle(1338, "", "Text of a message.", "some_screen_id")
    assert not NotificationRequestBatch([notification]).validate_single(notification)


def test_notification_proto_without_content(mock_log):
    '''Test that a notification proto without content fails validation'''
    notification = NotificationRequestSingle(1338, "Msg title", None, "some_screen_id")
    assert not NotificationRequestBatch([notification]).validate_single(notification)


def test_notification_proto_empty_content(mock_log):
    '''Test that a notification proto with empty content fails validation'''
    notification = NotificationRequestSingle(1338, "Msg title", "", "some_screen_id")
    assert not NotificationRequestBatch([notification]).validate_single(notification)


def test_valid_notification_proto_without_screen(mock_log):
    '''Test that a valid notification proto without screen is validated correctly.'''
    notification = NotificationRequestSingle(1338, "Msg title", "Text of a message.")
    assert NotificationRequestBatch([notification]).validate_single(notification)


def test_valid_notification_proto_empty_screen(mock_log):
    '''Test that a valid notification proto with empty screen is validated correctly.'''
    notification = NotificationRequestSingle(1338, "Msg title", "Text of a message.", "")
    assert NotificationRequestBatch([notification]).validate_single(notification)


def test_notification_proto_empty_screen_process(mocker, mock_log):
    '''Test that a valid notification proto without screen can be processed.'''
    mocker.patch('pushkin.database.database.get_raw_messages')
    notification = NotificationRequestSingle(1338, "Msg title", "Text of a message.")
    NotificationRequestBatch([notification]).process_single(notification)
    database.get_raw_messages.assert_called_with(1338, "Msg title", "Text of a message.", "", config.game,
                                                 config.world_id, config.dry_run)
