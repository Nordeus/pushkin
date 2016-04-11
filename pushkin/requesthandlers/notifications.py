'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from pushkin.protobuf import PushNotificationMessage_pb2
from batch import BatchHandler
from pushkin.request.requests import NotificationRequestBatch
from pushkin.request.request_validators import ProtoNotificationValidator, JsonNotificationValidator
from pushkin.request.requests import NotificationRequestSingle
import json

class ProtoNotificationHandler(BatchHandler):
    """Http handler for receiving proto notification batches."""

    def init_input_format(self, body):
        proto_request = PushNotificationMessage_pb2.BatchNotificationRequest()
        proto_request.ParseFromString(body)
        return proto_request

    def unpack_batch(self, request_proto):
        return request_proto.notifications

    def create_request(self, requests):
        valid_requests = []
        validator = ProtoNotificationValidator()
        for request in requests:
            if validator.validate_single(request):
                valid_requests.append(NotificationRequestSingle(request.login_id, request.title, request.content))

        return NotificationRequestBatch(valid_requests)


class JsonNotificationHandler(BatchHandler):
    """Http handler for receiving JSON notification batches."""

    def init_input_format(self, body):
        return json.loads(body)

    def unpack_batch(self, request):
        return request['notifications']

    def create_request(self, requests):
        valid_requests = []
        validator = JsonNotificationValidator()
        for request in requests:
            if validator.validate_single(request):
                valid_requests.append(NotificationRequestSingle(request['login_id'], request['title'], request['content']))

        return NotificationRequestBatch(valid_requests)