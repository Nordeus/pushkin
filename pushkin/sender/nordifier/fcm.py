'''
The MIT License (MIT)

Copyright (c) 2012 Minh Nam Ngo.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import firebase_admin
from firebase_admin import credentials, messaging

FCM_URL = 'https://fcm.googleapis.com/fcm/send'


class FCMException(Exception):
    pass


class FCMInvalidMessageException(FCMException):
    pass


class FCMTooManyRegIdsException(FCMException):
    pass


def generate_fcm_app(service_account_file):
    cred = credentials.Certificate(service_account_file)
    default_app = firebase_admin.initialize_app(cred)
    return default_app


class FCM(object):
    def __init__(self, app):
        """ app : FCM app
        """
        self.app = app

    def send(self, data, dry_run=False):
        try:
            response = messaging.send(data, dry_run=dry_run, app=self.app)
        except messaging.ApiCallError as e:
            raise FCMException(e)
        except Exception as e:
            raise FCMInvalidMessageException(e)
        return response

    def send_batch(self, data, dry_run=False):
        response = messaging.send_all(data, dry_run=dry_run, app=self.app)
        if response.failure_count > 0:
            raise FCMTooManyRegIdsException("Many reg id is failed %s",
                                            ",".join(response.responses["failed_registration_ids"]))
        return response
