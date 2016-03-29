'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import time


class Sender:
    def __init__(self, config, log):
        self.queue = []
        self.config = config
        self.log = log

        self.connection_error_retries = config.getint('Messenger', 'connection_error_retries')
        self.batch_size = 1

    def send_in_batch(self, notification):
        self.queue.append(notification)
        if len(self.queue) >= self.batch_size:
            self.send_batch()

    def send_remaining(self):
        while len(self.queue) > 0:
            self.send_batch()

    def send(self, notification):
        raise Exception('Not implemented')

    def send_batch(self):
        raise Exception('Not implemented')