'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import time

from sender import Sender
import constants as const
from gcm import GCM, GCMException, GCMConnectionException, GCMUnavailableException
from pyapn2.client import APNsClient
from datetime import datetime
from pyapn2.payload import Payload
from pyapn2.errors import APNsException, Unregistered


class APNS2PushSender(Sender):

    def __init__(self, config, log):
        Sender.__init__(self, config, log)
        self.sandbox = config.get('Messenger', 'apns_sandbox') == 'true'
        self.certificate_path = config.get('Messenger', 'apns_certificate_path')
        self.topic = config.get('Messenger', 'apns_topic')
        self.apn = APNsClient(self.certificate_path, use_sandbox=self.sandbox)
        self.canonical_ids = []
        self.unregistered_devices = []

    def get_canonical_ids(self):
        return self.canonical_ids

    def get_unregistered_devices(self):
        return self.unregistered_devices

    def prepare_data(self, notification):
        def to_timestamp(dt, epoch=datetime(1970, 1, 1)):
            # http://stackoverflow.com/questions/8777753/converting-datetime-date-to-utc-timestamp-in-python
            td = dt - epoch
            # return td.total_seconds() # Python 2.7
            return (td.microseconds + (td.seconds + td.days * 86400) * 10 ** 6) / 10 ** 6

        expiry_seconds = (notification['time_to_live_ts_bigint'] - int(round(time.time() * 1000))) / 1000
        expiry_utc_ts_seconds = to_timestamp(datetime.utcnow()) + expiry_seconds

        if expiry_seconds < 0:
            self.log.warning('APNS2: expired notification with sending_id: {0}; expiry_seconds: {1}'.format(
                notification['sending_id'], expiry_seconds))
            notification['status'] = const.NOTIFICATION_EXPIRED
            return None

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
        data = self.prepare_data(notification)

        if data is not None:
            for i in xrange(self.connection_error_retries):
                try:
                    self.apn.send_notification(data['token'], data['payload'], expiration=data['expiry'], topic=self.topic)
                    break #We did it, time to break free!
                except APNsException as e:
                    if isinstance(e, Unregistered):
                        notification['status'] = const.NOTIFICATION_APNS_DEVICE_UNREGISTERED
                        unregistered_data = {
                                        'login_id': notification['login_id'],
                                        'device_token': notification['receiver_id'],
                                    }
                        self.unregistered_devices.append(unregistered_data)
                    else:
                        self.log.warning('APN got exception {}'.format(e))

    def send_batch(self):
        while len(self.queue):
            self.send(self.queue.pop())
    
