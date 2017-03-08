import mock
import pytest

from pushkin.sender.nordifier import constants
from pushkin.sender import sender_manager


APN = 'pushkin.sender.senders.ApnNotificationSender'
GCM = 'pushkin.sender.senders.GcmNotificationSender'


@mock.patch('pushkin.sender.sender_manager.config')
def test_sender_manager_init_no_senders_given(mock_config):
    mock_config.enabled_senders.split.return_value=[]
    with pytest.raises(SystemExit) as ex:
        sender_manager.NotificationSenderManager()
    assert ("Nothing to start. At least one sender class "
            "must be specified in config") in str(ex)

@mock.patch(APN)
@mock.patch(GCM)
def test_sender_manager_init_bad_subclass(mock_gcm, mock_apn):
    with pytest.raises(SystemExit) as ex:
        sender_manager.NotificationSenderManager()
    assert ("Failed to load sender") in str(ex)
    assert ("TypeError") in str(ex)  # issubclass(<Mock()>... => TypeError

@mock.patch('pushkin.sender.sender_manager.issubclass',
            create=True, return_value=True)
@mock.patch(APN, PLATFORMS=(2, 5))
@mock.patch(GCM, PLATFORMS=(1, 6))
def test_sender_manager_init(mock_gcm, mock_apn, mock_issub):
    mngr = sender_manager.NotificationSenderManager()
    senders = {APN: mock_apn.return_value, GCM: mock_gcm.return_value}
    sender_names = {1: GCM, 6: GCM, 2: APN, 5: APN}
    assert mngr.sender_by_name == senders
    assert mngr.sender_name_by_platform == sender_names
    mock_gcm.assert_called_once_with(workers=30)
    mock_apn.assert_called_once_with(workers=10)

@mock.patch('pushkin.sender.sender_manager.issubclass',
            create=True, return_value=True)
@mock.patch(APN, PLATFORMS=(2, 5))
@mock.patch(GCM, PLATFORMS=(1, 6))
def test_sender_manager_start(mock_gcm, mock_apn, mock_issub):
    mngr = sender_manager.NotificationSenderManager()
    mngr.notification_post_processor = mock.Mock()
    assert not mngr.sender_by_name[APN].start.called
    assert not mngr.sender_by_name[GCM].start.called
    mngr.start()
    mngr.sender_by_name[APN].start.assert_called_once_with()
    mngr.sender_by_name[GCM].start.assert_called_once_with()
    mngr.notification_post_processor.start.assert_called_once_with()

@mock.patch('pushkin.sender.sender_manager.context')
@mock.patch('pushkin.sender.sender_manager.issubclass',
            create=True, return_value=True)
@mock.patch(APN, PLATFORMS=(2, 5))
@mock.patch(GCM, PLATFORMS=(1, 6))
def test_sender_manager_submit(mock_gcm, mock_apn, mock_issub, mock_context):
    mngr = sender_manager.NotificationSenderManager()
    apn_notification = {'platform': 2, 'login_id': 123, 'message_id': 42}
    gcm_notification = {'platform': 6, 'login_id': 321, 'message_id': 24}
    mngr.submit(apn_notification)
    mngr.submit(gcm_notification)
    mngr.sender_by_name[APN].submit.assert_called_once_with(apn_notification)
    mngr.sender_by_name[GCM].submit.assert_called_once_with(gcm_notification)
