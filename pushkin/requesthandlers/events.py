'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from pushkin.protobuf import EventMessage_pb2
from batch import BatchHandler
from pushkin.request.requests import EventRequestBatch
from pushkin.request.request_validators import ProtoEventValidator, JsonEventValidator
from pushkin.request.requests import EventRequestSingle
from pushkin import context
import json

class ProtoEventHandler(BatchHandler):
    """Http handler for receiving proto event batches."""

    def init_input_format(self, body):
        proto_request = EventMessage_pb2.BatchEventRequest()
        proto_request.ParseFromString(body)
        return proto_request

    def unpack_batch(self, request):
        return request.events

    def create_request(self, requests):
        valid_requests = []
        validator = ProtoEventValidator()
        for request in requests:
            if validator.validate_single(request):
                valid_requests.append(EventRequestSingle(request.user_id, request.event_id, {pair.key:pair.value for pair in request.pairs}, request.timestamp))
            else:
                context.main_logger.error("Request not valid: {req}".format(req=str(request.__dict__)))

        return EventRequestBatch(valid_requests)


class JsonEventHandler(BatchHandler):
    """Http handler for receiving JSON event batches."""

    def init_input_format(self, body):
        return json.loads(body)

    def unpack_batch(self, request):
        return request['events']

    def create_request(self, requests):
        valid_requests = []
        validator = JsonEventValidator()
        for request in requests:
            if validator.validate_single(request):
                valid_requests.append(EventRequestSingle(request['user_id'], request['event_id'], request['pairs'] if 'pairs' in request else {}, request['timestamp']))

        return EventRequestBatch(valid_requests)