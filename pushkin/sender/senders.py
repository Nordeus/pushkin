'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from Queue import Empty
import time
import logging

from pushkin.database import database
from pushkin.sender.nordifier.apns_push_sender import APNsPushSender
from pushkin.sender.nordifier.gcm_push_sender import GCMPushSender
from pushkin.util.pool import ProcessPool
from pushkin import context
from pushkin import config
from pushkin.sender.nordifier import constants


class NotificationSender(ProcessPool):
    def __init__(self, num_workers):
        ProcessPool.__init__(self, self.__class__.__name__, num_workers, config.sender_queue_limit)

    def limit_exceeded(self, notification):
        notification['status'] = constants.NOTIFICATION_SENDER_QUEUE_LIMIT
        self.log_notifications([notification])

    def queue_size(self):
        return self.task_queue.qsize()

    def log_notifications(self, notifications):
        main_logger = logging.getLogger(config.main_logger_name)
        notification_logger = logging.getLogger(config.notifications_logger_name)
        for notification in notifications:
            try:
                notification['content'] = notification['content'].encode('utf-8').replace(',', '\\,')
                keys = ['status', 'login_id', 'content', 'message_id', 'campaign_id', 'sending_id', 'game', 'world_id',
                        'screen', 'time', 'time_to_live_ts_bigint', 'platform', 'receiver_id']
                notification_logger.info(','.join([str(notification[key]) for key in keys]))
            except:
                main_logger.exception("Error while logging notification to csv log!")


class ApnNotificationSender(NotificationSender):
    def __init__(self):
        NotificationSender.__init__(self, config.apn_num_processes)
        self.apn_sender_interval_sec = config.apn_sender_interval_sec
        self.max_batch_size = config.sender_batch_size

    def send_batch(self, sender):
        """Tries to send up to max_batch_size notifications in a single batch.
        If there is < max_batch_size in queue, sender.send_remaining() will send the notifications.
        If there is > max_batch_size in queue, notifications will be sent by ender.send_in_batch in last iteration.
        """
        sent = []
        try:
            for i in xrange(self.max_batch_size):
                notification = self.task_queue.get_nowait()
                sender.send_in_batch(notification)
                sent.append(notification)
        except Empty:
            pass
        sender.send_remaining()
        return sent

    def process(self):
        main_logger = logging.getLogger(config.main_logger_name)
        while True:
            if self.queue_size() > 0:

                sender = None
                sent = []
                try:
                    sender = APNsPushSender(config.config, main_logger)
                    sent = self.send_batch(sender)
                    time.sleep(self.apn_sender_interval_sec)
                except Exception:
                    main_logger.exception("ApnNotificationProcessor failed to send notifications")
                finally:
                    if sender is not None:
                        sender.close_after_sending()
                    self.log_notifications(sent)
            else:
                time.sleep(self.apn_sender_interval_sec)


class GcmNotificationSender(NotificationSender):
    def __init__(self):
        NotificationSender.__init__(self, config.gcm_num_processes)

    def process(self):
        main_logger = logging.getLogger(config.main_logger_name)
        while True:
            notification = self.task_queue.get()
            try:
                sender = GCMPushSender(config.config, main_logger)
                sender.send_in_batch(notification)
                canonical_ids = sender.get_canonical_ids()
                if len(canonical_ids) > 0:
                    database.update_canonicals(canonical_ids)
                unregistered_devices = sender.get_unregistered_devices()
                if len(unregistered_devices) > 0:
                    database.update_unregistered_devices(unregistered_devices)
            except Exception:
                main_logger.exception("GcmNotificationProcessor failed to send notifications")
            finally:
                self.log_notifications([notification])
