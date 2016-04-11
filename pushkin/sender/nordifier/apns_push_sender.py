'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import time
from datetime import datetime

from sender import Sender
from apns import APNs, Frame, Payload, ER_IDENTIFER, set_logger
import constants as const


class APNsPushSender(Sender):
    def __init__(self, config, log):
        """
        APNs Push Sender uses MODIFIED (watch out if you want to update it) PyAPNs module: https://github.com/djacobs/PyAPNs
        APNs documentation: https://developer.apple.com/library/ios/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Chapters/CommunicatingWIthAPS.html#//apple_ref/doc/uid/TP40008194-CH101-SW4
        """
        Sender.__init__(self, config, log)
        self.sent_queue = {}
        self.batch_size = int(config.get('Messenger', 'apns_batch_size'))
        self.sandbox = config.get('Messenger', 'apns_sandbox') == 'true'
        self.certificate_path = config.get('Messenger', 'apns_certificate_path')

        set_logger(log)

        self.apns = APNs(use_sandbox=self.sandbox, cert_file=self.certificate_path, enhanced=True,
                         write_retries=self.connection_error_retries)
        self.apns.gateway_server.register_response_listener(self.process_malformed_notification)
        self.apns.gateway_server.register_error_listener(self.process_failed_notification)

    def close_after_sending(self):
        while (not self.apns.gateway_server.is_sending_finished()):
            time.sleep(1)
        self.apns.gateway_server.force_close()

    def process_malformed_notification(self, error_response):
        id = error_response[ER_IDENTIFER]
        notification = None
        if id in self.sent_queue:
            notification = self.sent_queue[id]
            notification['status'] = const.NOTIFICATION_APNS_MALFORMED_ERROR

        self.log.error('APNs Malformed notification: {0}'.format(notification))

    def process_failed_notification(self, notification_ids_list):
        self.log.warning('APNs Connection failed')
        for id in notification_ids_list:
            notif = self.sent_queue[id]
            notif['status'] = const.NOTIFICATION_CONNECTION_ERROR

    def prepare_data(self, notification):
        def totimestamp(dt, epoch=datetime(1970, 1, 1)):
            # http://stackoverflow.com/questions/8777753/converting-datetime-date-to-utc-timestamp-in-python
            td = dt - epoch
            # return td.total_seconds() # Python 2.7
            return (td.microseconds + (td.seconds + td.days * 86400) * 10 ** 6) / 10 ** 6

        expiry_seconds = (notification['time_to_live_ts_bigint'] - int(round(time.time() * 1000))) / 1000
        expiry_utc_ts_seconds = totimestamp(datetime.utcnow()) + expiry_seconds

        if expiry_seconds < 0:
            self.log.warning('APNs: expired notification with sending_id: {0}; expiry_seconds: {1}'.format(
                notification['sending_id'], expiry_seconds))
            notification['status'] = const.NOTIFICATION_EXPIRED
            return False

        custom = {
            'path': notification['screen'],
            'source': 'pushnotification',
            'campaign': str(notification['campaign_id']),
            'medium': str(notification['message_id']),
        }
        result = {
            'token': notification['receiver_id'],
            'identifier': notification['sending_id'],
            'expiry': expiry_utc_ts_seconds,
            'priority': 10,
        }
        result['payload'] = Payload(alert=notification['content'], badge=1, sound='default', custom=custom)

        return result

    def send(self, notification):
        notification['status'] = const.NOTIFICATION_SUCCESS
        self.sent_queue[notification['sending_id']] = notification

        data = self.prepare_data(notification)
        if data:
            self.apns.gateway_server.send_notification(
                token_hex=data['token'],
                payload=data['payload'],
                identifier=data['identifier'],
                expiry=data['expiry']
            )

    def send_batch(self):
        if len(self.queue) > 0:
            self.log.debug('Apns batch size: {0}'.format(len(self.queue)))
            frame = Frame()
            while len(self.queue) > 0:
                notification = self.queue.pop()

                notification['status'] = const.NOTIFICATION_SUCCESS
                self.sent_queue[notification['sending_id']] = notification

                data = self.prepare_data(notification)
                if data:
                    frame.add_item(
                        token_hex=data['token'],
                        payload=data['payload'],
                        identifier=data['identifier'],
                        expiry=data['expiry'],
                        priority=data['priority']
                    )

            # batch (frame) prepared, send it
            self.apns.gateway_server.send_notification_multiple(frame)

