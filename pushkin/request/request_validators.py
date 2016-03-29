'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import abc

class NotificationValidator():
    __metaclass__  = abc.ABCMeta

    def __init__(self):
        self.fields_to_check = ['login_id', 'title', 'content']

    @abc.abstractmethod
    def validate_single(self, request):
        raise NotImplementedError

class ProtoNotificationValidator(NotificationValidator):

    def __init__(self):
        super(ProtoNotificationValidator, self).__init__()

    def validate_single(self, request):
        for field in self.fields_to_check:
            if not request.HasField(field):
                return False

        return True

class JsonNotificationValidator(NotificationValidator):

    def __init__(self):
        super(JsonNotificationValidator, self).__init__()

    def validate_single(self, request):
        for field in self.fields_to_check:
            if field not in request:
                return False

        return True

class EventValidator():
    __metaclass__  = abc.ABCMeta

    def __init__(self):
        self.fields_to_check = ['user_id', 'event_id', 'timestamp']

    @abc.abstractmethod
    def validate_single(self, request):
        raise NotImplementedError

class JsonEventValidator(EventValidator):
    ''' Concrete implementation of EventValidator for JSON requests. '''
    def __init__(self):
        super(JsonEventValidator, self).__init__()

    def validate_single(self, request):
        for field in self.fields_to_check:
            if field not in request:
                return False

        return True

class ProtoEventValidator(EventValidator):
    ''' Concrete implementation of EventValidator for protobuff requests. '''

    def __init__(self):
        super(ProtoEventValidator, self).__init__()

    def validate_single(self, request):
        for field in self.fields_to_check:
            if not request.HasField(field):
                return False

        return True
