'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from collections import defaultdict
import re
from pushkin.database import database
from pushkin import context
from pushkin import config
from pushkin.util.tools import is_integer

"""A place for handling events. Currently only login event is handled, this should be dinamycally configured in future."""

class EventHandlerManager():
    """Responsible for invoking event handlers for given events."""

    def __init__(self):
        self._event_handler_map = defaultdict(list)
        self._build()

    def _add_event_handler(self, handler):
        self._event_handler_map[handler.event_id].append(handler)

    def _build(self):
        self._add_event_handler(LoginEventHandler())
        self._add_event_handler(TurnOffNotificationEventHandler())
        event_to_message_mapping = database.get_event_to_message_mapping()
        for event_id, message_ids in event_to_message_mapping.iteritems():
            self._add_event_handler(EventToMessagesHandler(event_id, message_ids))

    def get_handlers(self, event_id):
        return self._event_handler_map[event_id]

    def get_event_ids(self):
        return self._event_handler_map.keys()


class EventHandler():
    def __init__(self, event_id):
        self.event_id = event_id

    def handle_event(self, event, event_params):
        raise Exception("Not implemented!")

    def validate(self, event, event_params):
        return event.has_field('user_id') and event.has_field('timestamp')


class LoginEventHandler(EventHandler):
    """Writes user data to database on login event."""

    def __init__(self):
        EventHandler.__init__(self, config.login_event_id)

    def handle_event(self, event, event_params):
        database.process_user_login(login_id=event.user_id, language_id=event_params.get('languageId'),
                                    platform_id=event_params['platformId'],
                                    device_token=event_params.get('deviceToken'),
                                    application_version=event_params['applicationVersion'])
        return []

    def validate(self, event, event_params):
        result = EventHandler.validate(self, event, event_params)
        result &= is_integer(event_params.get('platformId', ''))
        result &= is_integer(event_params.get('applicationVersion', ''))
        return result

class TurnOffNotificationEventHandler(EventHandler):
    """ Writes data about notifications that user doesn't want to receive into database """

    def __init__(self):
        EventHandler.__init__(self, config.turn_off_notification_event_id)

    def handle_event(self, event, event_params):
        blacklist = set()

        for _, value in event_params.iteritems():
            blacklist.add(value)

        database.upsert_message_blacklist(event.user_id, list(blacklist))
        context.message_blacklist[event.user_id] = blacklist

        return []

    def validate(self, event, event_params):
        result = EventHandler.validate(self, event, event_params)
        for _, value in event_params.iteritems():
            result &= is_integer(value)

        return result

PARAM_REGEX = re.compile("\{[a-zA-Z0-9_]+\}")

class EventToMessagesHandler(EventHandler):
    """Creates localized messages based on event_id to message_id mapping"""

    def __init__(self, event_id, message_ids):
        EventHandler.__init__(self, event_id)
        if message_ids is None or len(message_ids) == 0:
            raise Exception("EventToMessagesHandler with event_id {} has no message ids!".format(event_id))
        self.message_ids = message_ids

    def handle_event(self, event, event_params):

        # Allowed characters for parameter name are [a-zA-Z0-9_]
        def get_parameter(param_name):
            parameter = event_params.get(param_name)
            if parameter is None:
                raise Exception("Parameter '{param_name}' required in localization is missing from event!".
                                format(param_name=param_name))
            if type(parameter) == unicode:
                parameter = parameter.encode('utf-8')
            return parameter

        def get_parameter_map(parametrized_text):
            parameter_names = [key.group(0).strip("{}") for key in
                               PARAM_REGEX.finditer(parametrized_text)]
            parameter_map = {
                param_name: get_parameter(param_name)
                for param_name in parameter_names
            }
            return parameter_map

        raw_messages = []
        if self.event_id == event.event_id:
            for message_id in self.message_ids:
                if message_id not in context.message_blacklist.get(event.user_id, set()):
                    try:
                        localized_message = database.get_localized_message(event.user_id, message_id)

                        if localized_message is not None:
                            text_parameter_map = get_parameter_map(localized_message.message_text)
                            title_parameter_map = get_parameter_map(localized_message.message_title)
                            raw_messages.extend(
                                database.get_raw_messages(
                                    login_id=event.user_id, title=localized_message.message_title.encode('utf-8').format(**title_parameter_map).decode('utf-8'),
                                    content=localized_message.message_text.encode('utf-8').format(**text_parameter_map).decode('utf-8'),
                                    screen=localized_message.message.screen, game=config.game, world_id=config.world_id,
                                    dry_run=config.dry_run, message_id=message_id, event_ts_bigint=event.timestamp,
                                    expiry_millis=localized_message.message.expiry_millis
                                ))
                        else:
                            context.main_logger.debug("Cannot get localization for user {login_id}".format(login_id=event.user_id))
                    except:
                        context.main_logger.exception(
                            'Problem with preparing message (message_id={message_id})'.format(message_id=message_id))
        else:
            context.main_logger.error('EventToMessagesHandler can handle event_id {handled_id} but got {passed_id}'
                                      .format(handled_id=self.event_id, passed_id=event.event_id))
        return raw_messages

    def validate(self, event, event_params):
        return True
