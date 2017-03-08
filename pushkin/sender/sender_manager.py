'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import json
import sys

from pushkin.sender.nordifier import constants
from pushkin.sender import senders
from pushkin import context
from pushkin import config


class NotificationSenderManager():

    def __init__(self):
        self.sender_by_name = {}
        self.sender_name_by_platform = {}

        values = [v.strip() for v in config.enabled_senders.split('\n')]
        values = filter(bool, values)

        if not values:
            sys.exit(u"Nothing to start. At least one sender class must "
                     u"be specified in config [Sender]enabled_senders")

        for value in values:
            cfg = value.split('{', 1)
            sender_name = cfg[0].strip()
            if not sender_name:
                sys.exit(u"Error: bad sender configuration: {}".format(cfg))
            try:
                kwargs = json.loads('{' + cfg[1])
            except IndexError:
                kwargs = {}
            except ValueError:
                sys.exit(u"Error: failed to parse JSON kwargs "
                         u"from sender configuration: {}".format(s))
            try:
                module, cls_name = sender_name.rsplit('.', 1)
                sender_cls = getattr(__import__(module, fromlist=[cls_name]),
                                     cls_name)
                if not issubclass(sender_cls, senders.NotificationSender):
                    raise AttributeError(
                        u"{} must be a subclass of senders.NotificationSender"
                        u"".format(sender_cls))
            except (ImportError, AttributeError, TypeError) as e:
                err = u"Failed to load sender '{}': {}: {}"
                sys.exit(err.format(sender_name, type(e).__name__, e))

            try:
                platforms = sender_cls.PLATFORMS
            except AttributeError:
                err = u"Failed to load sender: missed property {}.PLATFORMS"
                sys.exit(err.format(sender_name))

            if not platforms:
                err = u"Failed to load sender: empty {}.PLATFORMS"
                sys.exit(err.format(sender_name))

            sender_ins = sender_cls(**kwargs)

            for platform in map(int, platforms):
                if platform in self.sender_name_by_platform:
                    rival_name = self.sender_name_by_platform[platform]
                    err = (u"Failed to load sender '{}': platform '{}' "
                           u"is already registered by another sender '{}'")
                    sys.exit(err.format(sender_name, platform, rival_name))

                self.sender_name_by_platform[platform] = sender_name

            if config.main_log_level == context.logging.DEBUG:
                dmesg = u"Registering sender {}({}) for platforms: {}"
                args = ["{}={!r}".format(*i) for i in kwargs.items()]
                print (dmesg.format(sender_name, ', '.join(args),
                                    ', '.join(map(str, platforms))))
            self.sender_by_name[sender_name] = sender_ins

        self.notification_post_processor = senders.NotificationPostProcessor()

    def submit(self, notification):
        platform = notification['platform']
        if platform in self.sender_name_by_platform:
            sender_name = self.sender_name_by_platform[platform]
            sender_ins = self.sender_by_name[sender_name]

            dmesg = u"Submitting notification {} to sender {}"
            context.main_logger.debug(dmesg.format(notification, sender_name))

            sender_ins.submit(notification)
        else:
            context.main_logger.error("Unknown platform: {}".format(platform))

    def start(self):
        for sender_ins in self.sender_by_name.values():
            sender_ins.start()
        self.notification_post_processor.start()
