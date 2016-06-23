'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from logging.handlers import TimedRotatingFileHandler
from threading import Thread
import logging

"""Used to provide support for centralized logging for multiple processes.
Since logging in python is thread-safe but not process-safe, logging is centralized in main process
and synchronized through a queue.
"""


class QueueHandler(logging.Handler):
    """A logging handler that logs into a queue.

    Queue is common for all loggers, logger_name has to be added to every record.
    """
    def __init__(self, queue, logger_name):
        logging.Handler.__init__(self)
        self.queue = queue
        self.logger_name = logger_name

    def enqueue(self, record):
        self.queue.put_nowait(record)

    def prepare(self, record):
        self.format(record)
        record.msg = record.message
        record.logger_name = self.logger_name
        record.args = None
        record.exc_info = None
        return record

    def emit(self, record):
        try:
            self.enqueue(self.prepare(record))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

class LogCollector(Thread):
    """Should be run in main thread after configuring logging.

    It reads queue filled from sub processes and logs into persist logger.
    """
    def __init__(self, log_queue):
        Thread.__init__(self)
        self.log_queue = log_queue
        self.daemon = True

    def run(self):
        while True:
            try:
                record = self.log_queue.get()
                logger = logging.getLogger(record.logger_name)
                logger.handle(record)
            except:
                pass


def create_multiprocess_logger(logger_name, persist_logger_name, log_level, log_format, log_queue, log_file_path,
                               when_to_rotate, keep_log_days, log_suffix=None):
    """
    Creates queue logger and persist logger.

    Queue logger should be used to log into. It is Thread and Process safe.
    Persist logger is logger which persist data to disk. LogCollector moves data from queue log into persist log.
    """

    queue_log_formatter = logging.Formatter(log_format)
    queue_log_handler = QueueHandler(log_queue, persist_logger_name)
    queue_log_handler.setFormatter(queue_log_formatter)
    queue_logger = logging.getLogger(logger_name)
    queue_logger.setLevel(log_level)
    queue_logger.handlers = []
    queue_logger.addHandler(queue_log_handler)
    queue_logger.propagate = False

    persist_log_formatter = logging.Formatter('%(message)s')
    persist_log_handler = TimedRotatingFileHandler(log_file_path, when=when_to_rotate, interval=1, backupCount=keep_log_days)
    if log_suffix is not None:
        persist_log_handler.suffix = log_suffix
    persist_log_handler.setFormatter(queue_log_formatter)
    persist_logger = logging.getLogger(persist_logger_name)
    persist_logger.setLevel(log_level)
    persist_logger.handlers = []
    persist_logger.addHandler(persist_log_handler)
    persist_logger.propagate = False
