'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from pushkin import context
from pushkin import config
from pushkin.database import database


class AbstractRequest():
    def has_field(self, field):
        if self.__dict__.get(field) is not None and self.__dict__.get(field) != '':
            return True
        else:
            return False


class NotificationRequestSingle(AbstractRequest):
    def __init__(self, login_id, title, content, screen=''):
        self.login_id = login_id
        self.title = title
        self.content = content
        self.screen = screen


class NotificationRequestBatch():
    """Encapsulates a batch of notifications ready for processing."""

    def __init__(self, notifications):
        self.notifications = notifications

    def process(self):
        for notification in self.notifications:
            try:
                if self.validate_single(notification):
                    self.process_single(notification)
                else:
                    context.main_logger.error("Notification proto is not valid: {}".format(notification))
            except:
                context.main_logger.exception("Error while processing notification proto: {}".format(notification))

    def process_single(self, notification):
        raw_messages = database.get_raw_messages(notification.login_id, notification.title, notification.content,
                                                 notification.screen, config.game, config.world_id, config.dry_run)
        if len(raw_messages) > 0:
            for raw_message in raw_messages:
                context.main_logger.debug("Submitting to NotificationSender: {}".format(raw_message))
                context.request_processor.sender_manager.submit(raw_message)
        else:
            context.main_logger.debug("No device for user {login_id}, notification not sent".format(login_id=notification.login_id))

    def validate_single(self, notification):
        """Validate a single notification proto."""
        result = True
        result = result and notification.has_field('login_id')
        result = result and notification.has_field('title')
        result = result and notification.has_field('content')
        return result

    def __repr__(self):
        return "NotificationsRequests({})".format(len(self.notifications))

    def __str__(self):
        return "NotificationsRequests({})".format(len(self.notifications))


class EventRequestSingle(AbstractRequest):
    def __init__(self, user_id, event_id, pairs, timestamp=None):
        self.user_id = user_id
        self.event_id = event_id
        self.pairs = pairs
        self.timestamp = timestamp


class EventRequestBatch():
    """Encapsulates a batch of events ready for processing."""

    def __init__(self, events):
        self.events = events

    def process(self):
        messages = self.build_messages()
        for message in self.filter_messages(messages):
            context.request_processor.sender_manager.submit(message)

    def build_messages(self):
        """Creates a list of messages if there are registered event handlers"""
        messages = []
        for event in self.events:
            try:
                event_params = event.pairs
                if self.validate_single(event, event_params):
                    new_messages = self.process_single(event, event_params)
                    messages.extend(new_messages)
                else:
                    context.main_logger.error("Event proto is not valid: {}".format(event))
            except Exception as e:
                context.main_logger.exception("Error while processing event proto: {}".format(event))
        return messages

    def filter_messages(self, messages):
        """Filters out messages that shouldn't be send according to cooldown"""
        if len(messages) > 0:
            pairs = {(message['login_id'], message['message_id']) for message in messages}
            pairs_to_send = database.get_and_update_messages_to_send(pairs)
            if pairs_to_send is not None and len(pairs_to_send) > 0:
                # converts [{user_id: message_id}, ...] to [(user_id, message_id), ...]
                pairs_to_send_tuple = set([(pair.iteritems().next()) for pair in pairs_to_send])
                return [message for message in messages if
                        (str(message['login_id']), str(message['message_id'])) in pairs_to_send_tuple]
            else:
                return []
        return messages

    def process_single(self, event, event_params):
        messages = []
        handlers = context.event_handler_manager.get_handlers(event.event_id)
        for handler in handlers:
            context.main_logger.debug(
                "Handling event: {event} with handler: {handler}".format(event=event, handler=handler.__class__))
            messages.extend(handler.handle_event(event, event_params))
        return messages

    def validate_single(self, event, event_params):
        """Validate a single event proto."""
        handlers = context.event_handler_manager.get_handlers(event.event_id)
        for handler in handlers:
            if not handler.validate(event, event_params):
                return False
        return True

    def __repr__(self):
        return "EventRequests({})".format(len(self.events))

    def __str__(self):
        return "EventRequests({})".format(len(self.events))
