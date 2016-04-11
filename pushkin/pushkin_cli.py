#!/usr/bin/env python2
import argparse
import tornado.httpserver
import tornado.ioloop
import tornado.web
import atexit
import sys
import signal
import os
import os.path
from pushkin.requesthandlers.events import ProtoEventHandler, JsonEventHandler
from pushkin.requesthandlers.notifications import ProtoNotificationHandler, JsonNotificationHandler
from pushkin.request.request_processor import RequestProcessor
from pushkin.request.event_handlers import EventHandlerManager
from pushkin.requesthandlers.monitoring import RequestQueueHandler
from pushkin.requesthandlers.monitoring import ApnSenderQueueHandler
from pushkin.requesthandlers.monitoring import GcmSenderQueueHandler
import multiprocessing

from pushkin import context
from pushkin.database import database
from pushkin import config


CONFIGURATION_FILENAME = None
def init():
    context.setup_configuration(CONFIGURATION_FILENAME)
    database.init_db()

    context.log_queue = multiprocessing.Queue()
    context.request_processor = RequestProcessor()
    context.event_handler_manager = EventHandlerManager()


def create_app():
    application = tornado.web.Application([
        (config.proto_event_handler_url, ProtoEventHandler),
        (config.proto_notification_handler_url, ProtoNotificationHandler),
        (config.json_event_handler_url, JsonEventHandler),
        (config.json_notification_handler_url, JsonNotificationHandler),
        (config.request_queue_handler_url, RequestQueueHandler),
        (config.apn_sender_queue_handler_url, ApnSenderQueueHandler),
        (config.gcm_sender_queue_handler_url, GcmSenderQueueHandler),
    ])
    return application


def start():
    """Starts the server"""
    os.umask(022)
    context.setup_loggers()
    context.main_logger.info("Starting Pushkin...")
    context.main_logger.info("Starting processors...")
    context.start_processors()

    # register server to termination signals so we can stop the server
    # otherwise, server runs until killed
    def shutdown_handler(signum, frame):
        context.main_logger.info("Stopping Pushkin...")
        print "Server stopped."
        exit_handler()
        sys.exit(0)

    @atexit.register
    def exit_handler():
        tornado.ioloop.IOLoop.instance().stop()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    if os.name == 'nt':
        signal.signal(signal.SIGBREAK, shutdown_handler)
    else:
        signal.signal(signal.SIGQUIT, shutdown_handler)

    # start server
    server = tornado.httpserver.HTTPServer(create_app())
    server.bind(context.config.port)  # port
    server.start(1)
    context.main_logger.info("Pushkin has started")
    tornado.ioloop.IOLoop.instance().start()


def run():
    init()
    start()


def main():
    global CONFIGURATION_FILENAME

    parser = argparse.ArgumentParser(description='Service for sending push notifications')
    parser.add_argument('--configuration', dest='configuration_filename', required=True, help='Configuration file')
    parser.add_argument('--init-db', help='Initialize database', action='store_true')

    args = parser.parse_args()
    absolute_configuration_path = os.path.abspath(args.configuration_filename)

    CONFIGURATION_FILENAME = absolute_configuration_path

    if args.init_db:
        context.setup_configuration(CONFIGURATION_FILENAME)
        database.init_db()
        database.create_database()
    else:
        run()

if __name__ == '__main__':
    main()
