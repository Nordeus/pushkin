'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import pytest
from pushkin.request.event_handlers import EventHandler, EventHandlerManager
from pushkin.database import database


class EventHandlerA1(EventHandler):
    def __init__(self):
        EventHandler.__init__(self, 1)

    def handle_event(self, event_request):
        pass


class EventHandlerB1(EventHandler):
    def __init__(self):
        EventHandler.__init__(self, 1)

    def handle_event(self, event_request):
        pass


class EventHandlerA2(EventHandler):
    def __init__(self):
        EventHandler.__init__(self, 2)

    def handle_event(self, event_request):
        pass


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


@pytest.fixture
def manager():
    # mock event handlers
    manager = EventHandlerManager()
    manager._event_handler_map.clear()
    manager._add_event_handler(EventHandlerA1())
    manager._add_event_handler(EventHandlerB1())
    manager._add_event_handler(EventHandlerA2())
    return manager


def test_non_handled_event(setup, manager):
    '''Test that empty list is returned for non handled events.'''
    assert manager.get_handlers(3) == []


def test_handled_event_one_handler(setup, manager):
    '''Test that handler is returned for events with one handler'''
    handlers = manager.get_handlers(2)
    assert len(handlers) == 1
    assert handlers[0].__class__ == EventHandlerA2


def test_handled_event_multiple_handlers(setup, manager):
    '''Test that all handlers are returned for events with multiple handlers.'''
    handlers = manager.get_handlers(1)
    assert len(handlers) == 2
    assert handlers[0].__class__ == EventHandlerA1
    assert handlers[1].__class__ == EventHandlerB1


def test_event_ids(setup, manager):
    '''Test that correct event ids are returned.'''
    event_ids = manager.get_event_ids()
    assert event_ids == [1, 2]


def test_event_manager_event_mapping_handlers(setup):
    """Test of event mapping handlers are properly created according to data in db."""
    manager = EventHandlerManager()
    assert manager.get_handlers(0) == []
    handlers_1 = manager.get_handlers(1)
    assert len(handlers_1) == 1
    assert handlers_1[0].event_id == 1
    assert set(handlers_1[0].message_ids) == set([1, 2])

    handlers_2 = manager.get_handlers(2)
    assert len(handlers_2) == 1
    assert handlers_2[0].event_id == 2
    assert set(handlers_2[0].message_ids) == set([3])