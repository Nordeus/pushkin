'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import threading
import time

from pushkin.util.pool import ThreadPool
from pushkin import context
from pushkin import config
from pushkin.sender.sender_manager import NotificationSenderManager


class RequestProcessor(ThreadPool):
    """Background thread pool for doing blocking tasks from server requests and offloading notifications to other processes."""

    def __init__(self):
        ThreadPool.__init__(self, self.__class__.__name__, config.request_processor_num_threads,
                            config.request_queue_limit)
        self.sender_manager = NotificationSenderManager()

    def process(self):
        while True:
            item = self.task_queue.get()
            t0 = time.time()
            worker_name = threading.current_thread().name
            try:
                item.process()
                context.main_logger.debug(
                    "{worker} took: {took} seconds to process {item}".format(worker=worker_name, took=time.time() - t0,
                                                                             item=item.__class__.__name__))
            except Exception:
                context.main_logger.exception("RequestProcessor failed to process item: {}".format(item))

    def start(self):
        ThreadPool.start(self)
        self.sender_manager.start()
