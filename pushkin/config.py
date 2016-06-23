'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import ConfigParser
import logging
import os

"""Global configuration loaded from configuration file."""

DATABASE_CONFIG_SECTION = 'Database'
SERVER_SPECIFIC_CONFIG_SECTION = 'ServerSpecific'
EVENT_CONFIG_SECTION = 'Event'
LOG_CONFIG_SECTION = 'Log'
SERVER_CONFIG_SECTION = 'Server'
MESSENGER_CONFIG_SECTION = 'Messenger'
REQUEST_PROCESSOR_CONFIG_SECTION = 'RequestProcessor'
SENDER_CONFIG_SECTION = 'Sender'
REQUEST_HANDLER_SECTION = 'RequestHandler'

log_levels = {
    'notset': logging.NOTSET,
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}

def init(configuration_file):
    global db_name
    global db_user
    global db_pass
    global db_pool_size
    global max_devices_per_user
    global sqlalchemy_url
    global config
    global game
    global world_id
    global port
    global request_queue_limit
    global sender_batch_size
    global sender_queue_limit
    global apn_sender_interval_sec
    global gcm_num_processes
    global apn_num_processes
    global dry_run
    global request_processor_num_threads
    global login_event_id
    global turn_off_notification_event_id
    global main_log_path
    global main_log_level
    global main_log_file_path
    global notification_log_path
    global notification_log_file_path
    global notification_log_when_to_rotate
    global notification_log_rotate_suffix
    global keep_log_days
    global main_logger_name
    global notifications_logger_name
    global proto_event_handler_url
    global proto_notification_handler_url
    global json_event_handler_url
    global json_notification_handler_url
    global request_queue_handler_url
    global apn_sender_queue_handler_url
    global gcm_sender_queue_handler_url

    config = ConfigParser.ConfigParser()
    config.read(configuration_file)

    # server/game specifics
    game = config.get(SERVER_SPECIFIC_CONFIG_SECTION, 'game')
    world_id = config.get(SERVER_SPECIFIC_CONFIG_SECTION, 'world_id')
    port = config.get(SERVER_SPECIFIC_CONFIG_SECTION, 'port')

    # logging
    main_log_path = config.get(LOG_CONFIG_SECTION, 'main_log_path')
    main_log_level = log_levels[config.get(LOG_CONFIG_SECTION, 'main_log_level').lower()]
    main_log_file_path = os.path.join(main_log_path, 'pushkin.log')
    notification_log_path = config.get(LOG_CONFIG_SECTION, 'notification_log_path')
    notification_log_file_path = notification_log_path + 'notifications.csv'
    notification_log_when_to_rotate = config.get(LOG_CONFIG_SECTION, 'notification_log_when_to_rotate')
    notification_log_rotate_suffix = config.get(LOG_CONFIG_SECTION, 'notification_log_rotate_suffix')
    keep_log_days = config.getint(LOG_CONFIG_SECTION, 'keep_log_days')
    main_logger_name = config.get(LOG_CONFIG_SECTION, 'main_logger_name')
    notifications_logger_name = config.get(LOG_CONFIG_SECTION, 'notifications_logger_name')

    # processing
    request_queue_limit = config.getint(REQUEST_PROCESSOR_CONFIG_SECTION, 'queue_limit')
    sender_batch_size = config.getint(MESSENGER_CONFIG_SECTION, 'apns_batch_size')
    sender_queue_limit = config.getint(SENDER_CONFIG_SECTION, 'sender_queue_limit')
    apn_sender_interval_sec = config.getint(SENDER_CONFIG_SECTION, 'apn_sender_interval_sec')
    gcm_num_processes = config.getint(SENDER_CONFIG_SECTION, 'gcm_num_processes')
    apn_num_processes = config.getint(SENDER_CONFIG_SECTION, 'apn_num_processes')
    dry_run = config.getboolean(MESSENGER_CONFIG_SECTION, 'dry_run')
    request_processor_num_threads = config.getint(REQUEST_PROCESSOR_CONFIG_SECTION, 'request_processor_num_threads')

    # events
    login_event_id = config.getint(EVENT_CONFIG_SECTION, 'login_event_id')
    turn_off_notification_event_id = config.getint(EVENT_CONFIG_SECTION, 'turn_off_notification_event_id')

    # database
    db_name = config.get(DATABASE_CONFIG_SECTION, 'db_name')
    db_user = config.get(DATABASE_CONFIG_SECTION, 'db_user')
    db_pass = config.get(DATABASE_CONFIG_SECTION, 'db_pass')
    db_pool_size = int(config.get(DATABASE_CONFIG_SECTION, 'db_pool_size'))
    max_devices_per_user = int(config.get(DATABASE_CONFIG_SECTION, 'max_devices_per_user'))
    sqlalchemy_url = 'postgresql+psycopg2://{db_user}:{db_pass}@localhost:5432/{db_name}'.\
        format(db_user=db_user, db_pass=db_pass, db_name=db_name)

    #Handler URLs
    proto_event_handler_url = config.get(REQUEST_HANDLER_SECTION, 'proto_event_handler_url')
    proto_notification_handler_url = config.get(REQUEST_HANDLER_SECTION, 'proto_notification_handler_url')
    json_event_handler_url = config.get(REQUEST_HANDLER_SECTION, 'json_event_handler_url')
    json_notification_handler_url = config.get(REQUEST_HANDLER_SECTION, 'json_notification_handler_url')
    request_queue_handler_url = config.get(REQUEST_HANDLER_SECTION, 'request_queue_handler_url')
    apn_sender_queue_handler_url = config.get(REQUEST_HANDLER_SECTION, 'apn_sender_queue_handler_url')
    gcm_sender_queue_handler_url = config.get(REQUEST_HANDLER_SECTION, 'gcm_sender_queue_handler_url')
