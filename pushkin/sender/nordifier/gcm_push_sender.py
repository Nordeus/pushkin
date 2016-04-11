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


class GCMPushSender(Sender):
    """
    GCM Push Sender uses python-gcm module: https://github.com/geeknam/python-gcm
    GCM documentation: https://developer.android.com/google/gcm/gcm.html
    """

    def __init__(self, config, log):
        Sender.__init__(self, config, log)
        self.access_key = config.get('Messenger', 'gcm_access_key')
        self.base_deeplink_url = config.get('Messenger', 'base_deeplink_url')
        self.gcm = GCM(self.access_key)
        self.canonical_ids = []
        self.unregistered_devices = []

    def get_canonical_ids(self):
        return self.canonical_ids

    def get_unregistered_devices(self):
        return self.unregistered_devices

    def send(self, notification):
        expiry_seconds = (notification['time_to_live_ts_bigint'] - int(round(time.time() * 1000))) / 1000
        if expiry_seconds < 0:
            self.log.warning(
                'GCM: expired notification with sending_id: {0}; expiry_seconds: {1}'.format(notification['sending_id'],
                                                                                             expiry_seconds))
            notification['status'] = const.NOTIFICATION_EXPIRED
            return

        utm_source = 'pushnotification'
        utm_campaign = str(notification['campaign_id'])
        utm_medium = str(notification['message_id'])
        data = {
            'title': notification['title'],
            'message': notification['content'],
            'url': self.base_deeplink_url + '://' + notification[
                'screen'] + '?utm_source=' + utm_source + '&utm_campaign=' + utm_campaign + '&utm_medium=' + utm_medium,
            'notifid': notification['campaign_id'],
        }

        try:
            for i in range(self.connection_error_retries):
                try:
                    dry_run = 'dry_run' in notification and notification['dry_run'] == True
                    response = self.gcm.json_request(
                        registration_ids=[notification['receiver_id']],
                        data=data,
                        time_to_live=expiry_seconds,
                        retries=self.connection_error_retries,
                        dry_run=dry_run
                    )
                    if 'errors' in response:
                        # Initially it's a Fatal Error, unless we determine exact error
                        notification['status'] = const.NOTIFICATION_GCM_FATAL_ERROR
                        for error, reg_id_array in response['errors'].items():
                            if len(reg_id_array) == 1:
                                reg_id = reg_id_array[0]

                                if error == 'InvalidRegistration':
                                    notification['status'] = const.NOTIFICATION_GCM_INVALID_REGISTRATION_ID
                                    self.log.error('GCM InvalidRegistration for notification: {0}'.format(notification))

                                if error == 'NotRegistered':
                                    notification['status'] = const.NOTIFICATION_GCM_DEVICE_UNREGISTERED
                                    unregistered_data = {
                                        'login_id': notification['login_id'],
                                        'device_token': notification['receiver_id'],
                                    }
                                    self.unregistered_devices.append(unregistered_data)

                        if notification['status'] == const.NOTIFICATION_GCM_FATAL_ERROR:
                            self.log.debug(
                                'Undefined fatal error, notification: {0}, response: {1}'.format(notification,
                                                                                                 response))
                    else:
                        notification['status'] = const.NOTIFICATION_SUCCESS

                    # If we got canonical id, that means that the notification is successfully sent,
                    # but we should use a new registration (canonical) id in future
                    if 'canonical' in response:
                        self.log.debug('GCM Canonical response: {0}'.format(response))

                        for reg_id, canonical_id in response['canonical'].items():
                            canonical = {
                                'login_id': notification['login_id'],
                                'old_token': reg_id,
                                'new_token': canonical_id
                            }
                            self.canonical_ids.append(canonical)

                    break
                except GCMConnectionException as e:
                    notification['status'] = const.NOTIFICATION_CONNECTION_ERROR
                    self.log.warning('GCM Connection error, failed in {0}th attempt'.format((i + 1)))
                    if (i + 1) < self.connection_error_retries:
                        delay = 1 + (i * 2)
                        time.sleep(delay)
                except GCMUnavailableException as e:
                    notification['status'] = const.NOTIFICATION_GCM_UNAVAILABLE
                    self.log.warning('GCM is unavailable, failed in {0}th attempt'.format((i + 1)))
                    if (i + 1) < self.connection_error_retries:
                        delay = 5 + (i * 2)
                        time.sleep(delay)
        except GCMException as e:
            notification['status'] = const.NOTIFICATION_GCM_FATAL_ERROR
            self.log.error('GCM Exception: "{0}"; while senidng notification: {1}'.format(e, notification))

    def send_batch(self):
        while len(self.queue):
            self.send(self.queue.pop())
    
