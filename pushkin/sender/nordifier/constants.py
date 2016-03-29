'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
# Social network types
SN_GUEST = 0
SN_FACEBOOK = 1
SN_GOOGLE = 2

# Platform types
PLATFORM_ANDROID = 1
PLATFORM_IPHONE = 2
PLATFORM_IPAD = 5
PLATFORM_ANDROID_TABLET = 6

# Common statuses, [-2 : 100)
NOTIFICATION_CONTROL_GROUP = -2
NOTIFICATION_READY = -1
NOTIFICATION_SUCCESS = 0
NOTIFICATION_UNKNOWN_ERROR = 1
NOTIFICATION_CONNECTION_ERROR = 2
NOTIFICATION_EXPIRED = 3
NOTIFICATION_UNKNOWN_PLATFORM = 4
NOTIFICATION_SENDER_QUEUE_LIMIT = 5

# GCM errors [100 : 200)
NOTIFICATION_GCM_FATAL_ERROR = 100
NOTIFICATION_GCM_UNAVAILABLE = 101
NOTIFICATION_GCM_INVALID_REGISTRATION_ID = 102
NOTIFICATION_GCM_DEVICE_UNREGISTERED = 103

# APNs errors [200 : 300)
NOTIFICATION_APNS_MALFORMED_ERROR = 200

# Other
TIME_TO_LIVE_HOURS = 6