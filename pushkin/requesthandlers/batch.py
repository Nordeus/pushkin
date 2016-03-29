'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import tornado.web
import httplib
import abc
from pushkin import context


class BatchHandler(tornado.web.RequestHandler):
    """Abstract handler for receiving request batches."""

    __metaclass__ = abc.ABCMeta

    def parse_request(self, body):
        # discard invalid requests
        if not body:
            context.main_logger.error("Request was empty in batch handler {}!".format(self.__class__.__name__))
            raise tornado.web.HTTPError(400)
        try:
            request_input = self.init_input_format(body)
            return request_input
        except:
            context.main_logger.error(
                "Request could not be parsed in batch handler {}!".format(self.__class__.__name__))
            raise tornado.web.HTTPError(400)

    def post(self):
        self.handle_request()

    @abc.abstractmethod
    def init_input_format(self, body):
        """Create batch proto object."""
        raise NotImplementedError

    @abc.abstractmethod
    def unpack_batch(self, request):
        """Get request proto list from batch proto."""
        raise NotImplementedError

    @abc.abstractmethod
    def create_request(self, requests):
        """Create request to encapsulate proto_requests objects.
        Passed to RequestProcessor.
        """
        raise NotImplementedError

    def handle_request(self):
        parsed_request = self.parse_request(self.request.body)
        unpacked_requests = self.unpack_batch(parsed_request)
        context.main_logger.debug("Received an event batch of {num_requests} requests in batch handler {handler}"
                                  .format(num_requests=len(unpacked_requests),
                                          handler=self.__class__.__name__))

        if not context.request_processor.submit(self.create_request(unpacked_requests)):
            context.main_logger.warning("RequestProcessor queue size limit reached, sending back off response...")
            self.set_status(httplib.SERVICE_UNAVAILABLE)
        else:
            self.set_status(httplib.OK)
