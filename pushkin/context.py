'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import logging
import os
from pushkin import config
from util.multiprocesslogging import LogCollector, create_multiprocess_logger

request_processor = None
event_handler_manager = None
log_queue = None
PERSIST_LOGGER_PREFFIX = 'persist_'
main_logger = None
notification_logger = None
message_blacklist = None

"""This module is used as a holder for global state in server process"""

def setup_loggers():
    """Should be called before using loggers"""
    global log_queue
    global PERSIST_LOGGER_PREFFIX
    global main_logger
    global notification_logger

    # setup folders
    if not os.path.exists(os.path.dirname(config.main_log_path)):
        os.makedirs(os.path.dirname(config.main_log_path))
    if not os.path.exists(os.path.dirname(config.notification_log_path)):
        os.makedirs(os.path.dirname(config.notification_log_path))

    # setup loggers
    create_multiprocess_logger(logger_name=config.main_logger_name, log_level=config.main_log_level,
                               persist_logger_name=PERSIST_LOGGER_PREFFIX + config.main_logger_name,
                               log_format='%(asctime)s %(levelname)s %(message)s', log_queue=log_queue,
                               log_file_path=config.main_log_file_path, when_to_rotate="midnight",
                               keep_log_days=config.keep_log_days)
    main_logger = logging.getLogger(config.main_logger_name)

    create_multiprocess_logger(logger_name=config.notifications_logger_name, log_level=logging.INFO,
                               persist_logger_name=PERSIST_LOGGER_PREFFIX + config.notifications_logger_name,
                               log_format='%(message)s', when_to_rotate=config.notification_log_when_to_rotate,
                               log_file_path=config.notification_log_file_path, keep_log_days=config.keep_log_days,
                               log_queue=log_queue, log_suffix=config.notification_log_rotate_suffix)
    notification_logger = logging.getLogger(config.notifications_logger_name)

    # start log collector thread
    log_collector = LogCollector(log_queue)
    log_collector.start()

def setup_configuration(configuration_filename):
    config.init(configuration_filename)

def start_processors():
    """Starts threads/processes needed for server request processing"""
    request_processor.start()
