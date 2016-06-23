import pytest
from pushkin import pushkin_cli
import tornado.web
from pushkin.protobuf import EventMessage_pb2
from pushkin.protobuf import PushNotificationMessage_pb2
from pushkin import context
from pushkin.database import database
from pushkin.request.request_processor import RequestProcessor
from pushkin.sender.sender_manager import NotificationSenderManager
from pushkin.requesthandlers.events import ProtoEventHandler
from pushkin.requesthandlers.notifications import ProtoNotificationHandler
from pushkin import test_config_ini_path
from pushkin import config


@pytest.fixture
def setup_database():
    database.create_database()


@pytest.fixture
def mock_processor(mocker):
    '''Mock request processor'''
    mocker.patch('pushkin.request.request_processor.RequestProcessor.submit')
    mocker.patch('pushkin.context.main_logger')
    mocker.patch('pushkin.sender.sender_manager.NotificationSenderManager.submit')


@pytest.fixture
def app():
    pushkin_cli.CONFIGURATION_FILENAME = test_config_ini_path
    pushkin_cli.init()
    return pushkin_cli.create_app()


@pytest.fixture
def notification_batch_proto():
    '''Returns a valid notification request'''
    notification_request_proto = PushNotificationMessage_pb2.BatchNotificationRequest()
    notification_proto = notification_request_proto.notifications.add()
    notification_proto.login_id = 1338
    notification_proto.title = "Msg title"
    notification_proto.content = "Text of a message."
    notification_proto.screen = "some_screen_id"
    return notification_request_proto.SerializeToString()


@pytest.fixture
def notification_batch_json():
    ''' Return a valid json request '''
    return '''
    {
    "events": [
            {
                "login_id" : 1338,
                "title" : "Msg title",
                "content" : "Text of a message",
                "screen" : "some_screen_id"
            }
        ]
    }
    '''

@pytest.fixture
def post_notification_url(base_url):
    return base_url + config.proto_notification_handler_url


@pytest.fixture
def event_batch_proto():
    '''Return a valid event request'''
    event_request_proto = EventMessage_pb2.BatchEventRequest()
    event_proto = event_request_proto.events.add()
    event_proto.user_id = 123
    event_proto.event_id = 1
    event_proto.event_type = 2
    event_proto.timestamp = 12345
    # add some parameters
    pair = event_proto.pairs.add()
    pair.key = 'some_constant'
    pair.value = '6'
    pair = event_proto.pairs.add()
    pair.key = 'world_id'
    pair.value = '1'
    return event_request_proto.SerializeToString()

@pytest.fixture
def event_batch_json():
    ''' Return a valid json request '''
    return '''
    {
    "events": [
            {
                "user_id" : 123,
                "event_id" : 1,
                "timestamp" : 12345,
                "pairs": {
                    "some_constant" : "6",
                    "world_id" : "1"
                }
            }
        ]
    }
    '''


@pytest.fixture
def post_event_url(base_url):
    return base_url + config.proto_event_handler_url


@pytest.mark.gen_test
@pytest.mark.parametrize("input", [
    (''),
    ('asd'),
])
def test_post_notification_empty_request(setup_database, mock_processor, http_client, post_notification_url, input):
    '''Test that server responds with 400 if invalid parameter is supplied to post_notification request'''
    request = tornado.httpclient.HTTPRequest(post_notification_url, method='POST', body=input)
    with pytest.raises(tornado.httpclient.HTTPError):
        yield http_client.fetch(request)
    assert not context.request_processor.submit.called


@pytest.mark.gen_test
def test_post_notification(setup_database, mock_processor, http_client, post_notification_url,
                           notification_batch_proto):
    '''Test that a valid request is succesfully parsed in post_notification'''
    request = tornado.httpclient.HTTPRequest(post_notification_url, method='POST', body=notification_batch_proto)
    response = yield http_client.fetch(request)
    assert response.code == 200
    assert context.request_processor.submit.called


@pytest.mark.gen_test
@pytest.mark.parametrize("input", [
    (''),
    ('asd'),
])
def test_post_event_empty_request(setup_database, mock_processor, http_client, post_event_url, input):
    '''Test that server responds with 400 if invalid parameter is supplied to post_event request'''
    request = tornado.httpclient.HTTPRequest(post_event_url, method='POST', body=input)
    with pytest.raises(tornado.httpclient.HTTPError):
        yield http_client.fetch(request)
    assert not context.request_processor.submit.called


@pytest.mark.gen_test
def test_post_event(setup_database, mock_processor, http_client, post_event_url, event_batch_proto):
    '''Test that a valid request is succesfully parsed in post_event'''
    context.request_processor.submit.return_value = True
    request = tornado.httpclient.HTTPRequest(post_event_url, method='POST', body=event_batch_proto)
    response = yield http_client.fetch(request)
    assert response.code == 200
    assert context.request_processor.submit.called


@pytest.mark.gen_test
def test_message_blacklist(setup_database, mock_processor, http_client, post_event_url, event_batch_proto):
    '''Test that a valid request is succesfully parsed in post_event'''
    context.request_processor.submit.return_value = True

    login = database.upsert_login(123, 7)
    database.upsert_message_blacklist(123, [1])
    context.request_processor.submit.return_value = True
    request = tornado.httpclient.HTTPRequest(post_event_url, method='POST', body=event_batch_proto)
    response = yield http_client.fetch(request)
    assert not context.request_processor.sender_manager.submit.called


@pytest.mark.gen_test
def test_post_event_service_unavailable(setup_database, mock_processor, http_client, post_event_url, event_batch_proto,
                                        app):
    '''Test that service_unavailable is returned if server load is more that expected'''
    context.request_processor.submit.return_value = False
    request = tornado.httpclient.HTTPRequest(post_event_url, method='POST', body=event_batch_proto)
    RequestProcessor.submit.return_value = False
    with pytest.raises(tornado.httpclient.HTTPError):
        yield http_client.fetch(request)
