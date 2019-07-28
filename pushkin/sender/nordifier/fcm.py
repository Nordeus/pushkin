'''
The MIT License (MIT)

Copyright (c) 2012 Minh Nam Ngo.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import urllib
import urllib2
import json
from collections import defaultdict
import time
import random
import firebase_admin
from firebase_admin import credentials

FCM_URL = 'https://fcm.googleapis.com/fcm/send'


class FCMException(Exception): pass


class FCMMalformedJsonException(FCMException): pass


class FCMConnectionException(FCMException): pass


class FCMAuthenticationException(FCMException): pass


class FCMTooManyRegIdsException(FCMException): pass


class FCMInvalidTtlException(FCMException): pass


# Exceptions from Google responses
class FCMMissingRegistrationException(FCMException): pass


class FCMMismatchSenderIdException(FCMException): pass


class FCMNotRegisteredException(FCMException): pass


class FCMMessageTooBigException(FCMException): pass


class FCMInvalidRegistrationException(FCMException): pass


class FCMUnavailableException(FCMException): pass


# TODO: Refactor this to be more human-readable
def group_response(response, registration_ids, key):
    # Pair up results and reg_ids
    mapping = zip(registration_ids, response['results'])
    # Filter by key
    filtered = filter(lambda x: key in x[1], mapping)
    # Only consider the value in the dict
    tupled = [(s[0], s[1][key]) for s in filtered]
    # Grouping of errors and mapping of ids
    if key is 'registration_id':
        grouping = {}
        for k, v in tupled:
            grouping[k] = v
    else:
        grouping = defaultdict(list)
        for k, v in tupled:
            grouping[v].append(k)

    if len(grouping) == 0:
        return
    return grouping


def urlencode_utf8(params):
    """
    UTF-8 safe variant of urllib.urlencode.
    http://stackoverflow.com/a/8152242
    """

    if hasattr(params, 'items'):
        params = params.items()

    params = (
        '='.join((
            urllib.quote_plus(k.encode('utf8'), safe='/'),
            urllib.quote_plus(v.encode('utf8'), safe='/')
        )) for k, v in params
    )

    return '&'.join(params)


def generate_token(service_account_file):
    cred = credentials.Certificate(service_account_file)
    default_app = firebase_admin.initialize_app(cred)
    return default_app.credential.get_access_token()


class FCM(object):
    # Timeunit is milliseconds.
    BACKOFF_INITIAL_DELAY = 1000;
    MAX_BACKOFF_DELAY = 1024000;

    def __init__(self, token, url=FCM_URL, proxy=None):
        """ api_key : google api key
            url: url of FCM service.
            proxy: can be string "http://host:port" or dict {'https':'host:port'}
        """
        self.access_token = token
        self.url = url
        if proxy:
            if isinstance(proxy, basestring):
                protocol = url.split(':')[0]
                proxy = {protocol: proxy}

            auth = urllib2.HTTPBasicAuthHandler()
            opener = urllib2.build_opener(urllib2.ProxyHandler(proxy), auth, urllib2.HTTPHandler)
            urllib2.install_opener(opener)

    def construct_payload(self, registration_ids, data=None, collapse_key=None,
                          delay_while_idle=False, time_to_live=None, is_json=True, dry_run=False):
        """
        Construct the dictionary mapping of parameters.
        Encodes the dictionary into JSON if for json requests.
        Helps appending 'data.' prefix to the plaintext data: 'hello' => 'data.hello'

        :return constructed dict or JSON payload
        :raises FCMInvalidTtlException: if time_to_live is invalid
        """

        if time_to_live:
            if time_to_live > 2419200 or time_to_live < 0:
                raise FCMInvalidTtlException("Invalid time to live value")

        if is_json:
            payload = {'registration_ids': registration_ids}
            if data:
                payload['data'] = data
        else:
            payload = {'registration_id': registration_ids}
            if data:
                plaintext_data = data.copy()
                for k in plaintext_data.keys():
                    plaintext_data['data.%s' % k] = plaintext_data.pop(k)
                payload.update(plaintext_data)

        if delay_while_idle:
            payload['delay_while_idle'] = delay_while_idle

        if time_to_live >= 0:
            payload['time_to_live'] = time_to_live

        if collapse_key:
            payload['collapse_key'] = collapse_key

        if dry_run:
            payload['dry_run'] = True

        if is_json:
            payload = json.dumps(payload)

        return payload

    def make_request(self, data, is_json=True):
        """
        Makes a HTTP request to FCM servers with the constructed payload

        :param data: return value from construct_payload method
        :raises FCMMalformedJsonException: if malformed JSON request found
        :raises FCMAuthenticationException: if there was a problem with authentication, invalid api key
        :raises FCMConnectionException: if FCM is screwed
        """

        headers = {
            'Authorization': 'key=%s' % self.access_token,
        }
        # Default Content-Type is defaulted to application/x-www-form-urlencoded;charset=UTF-8
        if is_json:
            headers['Content-Type'] = 'application/json'

        if not is_json:
            data = urlencode_utf8(data)
        req = urllib2.Request(self.url, data, headers)

        try:
            response = urllib2.urlopen(req).read()
        except urllib2.HTTPError as e:
            if e.code == 400:
                raise FCMMalformedJsonException("The request could not be parsed as JSON")
            elif e.code == 401:
                raise FCMAuthenticationException("There was an error authenticating the nordifier account")
            elif e.code == 503:
                raise FCMUnavailableException("FCM service is unavailable")
            else:
                error = "FCM service error: %d" % e.code
                raise FCMUnavailableException(error)
        except urllib2.URLError as e:
            raise FCMConnectionException(
                "There was an internal error in the FCM server while trying to process the request")

        if is_json:
            response = json.loads(response)
        return response

    def raise_error(self, error):
        if error == 'InvalidRegistration':
            raise FCMInvalidRegistrationException("Registration ID is invalid")
        elif error == 'Unavailable':
            # Plain-text requests will never return Unavailable as the error code.
            # http://developer.android.com/guide/google/FCM/FCM.html#error_codes
            raise FCMUnavailableException("Server unavailable. Resent the message")
        elif error == 'NotRegistered':
            raise FCMNotRegisteredException("Registration id is not valid anymore")
        elif error == 'MismatchSenderId':
            raise FCMMismatchSenderIdException("A Registration ID is tied to a certain group of senders")
        elif error == 'MessageTooBig':
            raise FCMMessageTooBigException("Message can't exceed 4096 bytes")

    def handle_plaintext_response(self, response):

        # Split response by line
        response_lines = response.strip().split('\n')
        # Split the first line by =
        key, value = response_lines[0].split('=')
        if key == 'Error':
            self.raise_error(value)
        else:
            if len(response_lines) == 2:
                return response_lines[1].split('=')[1]
            return

    def handle_json_response(self, response, registration_ids):
        errors = group_response(response, registration_ids, 'error')
        canonical = group_response(response, registration_ids, 'registration_id')

        info = {}
        if errors:
            info.update({'errors': errors})
        if canonical:
            info.update({'canonical': canonical})

        return info

    def extract_unsent_reg_ids(self, info):
        if 'errors' in info and 'Unavailable' in info['errors']:
            return info['errors']['Unavailable']
        return []

    def plaintext_request(self, registration_id, data=None, collapse_key=None,
                          delay_while_idle=False, time_to_live=None, retries=5, dry_run=False):
        """
        Makes a plaintext request to FCM servers

        :param registration_id: string of the registration id
        :param data: dict mapping of key-value pairs of messages
        :return dict of response body from Google including multicast_id, success, failure, canonical_ids, etc
        :raises FCMMissingRegistrationException: if registration_id is not provided
        """

        if not registration_id:
            raise FCMMissingRegistrationException("Missing registration_id")

        payload = self.construct_payload(
            registration_id, data, collapse_key,
            delay_while_idle, time_to_live, False, dry_run
        )

        attempt = 0
        backoff = self.BACKOFF_INITIAL_DELAY
        for attempt in range(retries):
            try:
                response = self.make_request(payload, is_json=False)
                return self.handle_plaintext_response(response)
            except FCMUnavailableException:
                sleep_time = backoff / 2 + random.randrange(backoff)
                time.sleep(float(sleep_time) / 1000)
                if 2 * backoff < self.MAX_BACKOFF_DELAY:
                    backoff *= 2

        raise IOError("Could not make request after %d attempts" % attempt)

