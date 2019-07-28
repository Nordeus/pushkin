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
from fcm import FCM, generate_token
from firebase_admin import messaging


class FCMPushSender(Sender):
    """
    FCM Push Sender uses python-FCM module: https://github.com/geeknam/python-FCM
    FCM documentation: https://developer.android.com/google/FCM/FCM.html
    """

    def __init__(self, config, log):
        Sender.__init__(self, config, log)
        self.access_key = generate_token(config.get('Messenger', 'google_application_credentials'))
        self.base_deeplink_url = config.get('Messenger', 'base_deeplink_url')
        self.FCM = FCM(self.access_key)
        self.canonical_ids = []
        self.unregistered_devices = []

    def pop_canonical_ids(self):
        items = self.canonical_ids
        self.canonical_ids = []
        return items

    def pop_unregistered_devices(self):
        items = self.unregistered_devices
        self.unregistered_devices = []
        return items

    def create_message(self, notification):
        expiry_seconds = (notification['time_to_live_ts_bigint'] - int(round(time.time() * 1000))) / 1000
        if expiry_seconds < 0:
            self.log.warning(
                'FCM: expired notification with sending_id: {0}; expiry_seconds: {1}'.format(notification['sending_id'],
                                                                                             expiry_seconds))
            notification['status'] = const.NOTIFICATION_EXPIRED
            return

        utm_source = 'pushnotification'
        utm_campaign = str(notification['campaign_id'])
        utm_medium = str(notification['message_id'])
        data = {
            'title': notification['title'],
            'message': notification['content'],
            'url': self.base_deeplink_url + '://' + notification['screen'] +
                   '?utm_source=' + utm_source + '&utm_campaign=' + utm_campaign + '&utm_medium=' + utm_medium,
            'notifid': notification['campaign_id'],
        }
        msg = messaging.Message(
            data=data,
            token=notification['receiver_id'],
        )
        return msg

    def send(self, notification):
        message = self.create_message(notification)
        response = messaging.send(message)

        return response

    def send_batch(self):
        messages = []
        while len(self.queue):
            messages.append(self.create_message(self.queue.pop()))
        messaging.send_all(messages)
