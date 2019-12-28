'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from threading import Thread
import logging
import multiprocessing

from pushkin.database import database
from pushkin.sender.nordifier.gcm_push_sender import GCMPushSender
from pushkin.sender.nordifier.apns2_push_sender import APNS2PushSender
from pushkin.sender.nordifier.fcm_push_sender import FCMPushSender
from pushkin.util.pool import ProcessPool
from pushkin import config, context
from pushkin.sender.nordifier import constants
import timeit


class NotificationSender(ProcessPool):
    NUM_WORKERS_DEFAULT = 50

    def __init__(self, **kwargs):
        num_workers = kwargs.get('workers', self.NUM_WORKERS_DEFAULT)
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


class NotificationOperation():
    """Represents operation which should be executed outside of process pool"""

    def __init__(self, operation, data):
        self.operation = operation
        self.data = data


class NotificationPostProcessor(Thread):
    UPDATE_CANONICALS = 1
    UPDATE_UNREGISTERED_DEVICES = 2
    OPERATION_QUEUE = multiprocessing.Queue()

    def __init__(self):
        Thread.__init__(self)
        self.daemon = True

    def queue_size(self):
        return self.OPERATION_QUEUE.qsize()

    def update_canonicals(self, canonical_ids):
        database.update_canonicals(canonical_ids)

    def update_unregistered_devices(self, unregistered_devices):
        database.update_unregistered_devices(unregistered_devices)

    def run(self):
        while True:
            try:
                record = NotificationPostProcessor.OPERATION_QUEUE.get()
                if record.operation == NotificationPostProcessor.UPDATE_CANONICALS:
                    self.update_canonicals(record.data)
                elif record.operation == NotificationPostProcessor.UPDATE_UNREGISTERED_DEVICES:
                    self.update_unregistered_devices(record.data)
                else:
                    context.main_logger.error(
                        "NotificationPostProcessor - unknown operation: {operation}".format(operation=record.operation))
            except:
                context.main_logger.exception("Exception while post processing notification.")
                pass


class NotificationStatistics:
    def __init__(self, name, logger, last_averages=100, log_time_seconds=30):
        self.name = name
        self.logger = logger
        self.last_averages = last_averages
        self.log_time_seconds = log_time_seconds
        self.last_time_logged = timeit.default_timer()
        self.running_average = 0
        self.last_start = 0

    def start(self):
        self.last_start = timeit.default_timer()

    def stop(self):
        elapsed = timeit.default_timer() - self.last_start
        self.running_average -= self.running_average / self.last_averages
        self.running_average += elapsed / self.last_averages
        elapsed_since_log = timeit.default_timer() - self.last_time_logged
        if elapsed_since_log > self.log_time_seconds:
            self.logger.info(
                'Average time for sending push for {name} is {avg}'.format(name=self.name, avg=self.running_average))
            self.last_time_logged = timeit.default_timer()


class ApnNotificationSender(NotificationSender):
    PLATFORMS = (constants.PLATFORM_IPHONE,
                 constants.PLATFORM_IPAD)

    def process(self):
        sender = APNS2PushSender(config.config, context.main_logger)
        statistics = NotificationStatistics('APN', context.main_logger)
        while True:
            notification = self.task_queue.get()
            try:
                statistics.start()
                sender.send_in_batch(notification)
                statistics.stop()
                unregistered_devices = sender.pop_unregistered_devices()
                if len(unregistered_devices) > 0:
                    NotificationPostProcessor.OPERATION_QUEUE.put(
                        NotificationOperation(NotificationPostProcessor.UPDATE_UNREGISTERED_DEVICES,
                                              unregistered_devices))
            except Exception:
                context.main_logger.exception("ApnNotificationProcessor failed to send notifications")
            finally:
                self.log_notifications([notification])


class GcmNotificationSender(NotificationSender):
    PLATFORMS = (constants.PLATFORM_ANDROID,
                 constants.PLATFORM_ANDROID_TABLET)

    def process(self):
        sender = GCMPushSender(config.config, context.main_logger)
        statistics = NotificationStatistics('GCM', context.main_logger)
        while True:
            notification = self.task_queue.get()
            try:
                statistics.start()
                sender.send_in_batch(notification)
                statistics.stop()
                canonical_ids = sender.pop_canonical_ids()
                if len(canonical_ids) > 0:
                    NotificationPostProcessor.OPERATION_QUEUE.put(
                        NotificationOperation(NotificationPostProcessor.UPDATE_CANONICALS, canonical_ids))
                unregistered_devices = sender.pop_unregistered_devices()
                if len(unregistered_devices) > 0:
                    NotificationPostProcessor.OPERATION_QUEUE.put(
                        NotificationOperation(NotificationPostProcessor.UPDATE_UNREGISTERED_DEVICES,
                                              unregistered_devices))
            except Exception:
                context.main_logger.exception("GcmNotificationProcessor failed to send notifications")
            finally:
                self.log_notifications([notification])


class FcmNotificationSender(NotificationSender):
    PLATFORMS = (constants.PLATFORM_ANDROID,
                 constants.PLATFORM_ANDROID_TABLET,
                 constants.PLATFORM_IPAD,
                 constants.PLATFORM_IPHONE)

    def process(self):
        sender = FCMPushSender(config.config, context.main_logger)
        statistics = NotificationStatistics('FCM', context.main_logger)
        while True:
            notification = self.task_queue.get()
            try:
                statistics.start()
                sender.send_in_batch(notification)
                statistics.stop()
                canonical_ids = sender.pop_canonical_ids()
                if len(canonical_ids) > 0:
                    NotificationPostProcessor.OPERATION_QUEUE.put(
                        NotificationOperation(NotificationPostProcessor.UPDATE_CANONICALS, canonical_ids))
                unregistered_devices = sender.pop_unregistered_devices()
                if len(unregistered_devices) > 0:
                    NotificationPostProcessor.OPERATION_QUEUE.put(
                        NotificationOperation(NotificationPostProcessor.UPDATE_UNREGISTERED_DEVICES,
                                              unregistered_devices))
            except Exception:
                context.main_logger.exception("GcmNotificationProcessor failed to send notifications")
            finally:
                self.log_notifications([notification])
