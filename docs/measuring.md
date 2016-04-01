# Measuring results

Results of notifications can be tracked by analyzing CSV files from notification log directory (default location of log file is `/var/log/pushkin/notification/notification.csv` and it's rotated daily). We plan to create a dashboard with various settings and statistics.

CSV file has following columns:

* `status` - status of notification, possible statuses are listed below
* `login_id` - id of user in your application
* `content` - content of notification sent to user
* `message_id` - id of notification in pushking database
* `campaign_id` - for future use
* `sending_id` - internal id of notification used when sending batch
* `game` - name of your game or application, can be set in `config.ini`
* `world_id` - parameter from `config.ini`, should be used to distinct instances of Pushkin
* `screen` - key for deep link
* `time` - unix timestamp in milliseconds, when notification was sent
* `time_to_live` - unix timestamp in milliseconds, after this time notification should not be delivered
* `platform` - id of platform
* `receiver_id` - device token at GCM or APN


Here are possible statuses:

```python
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
```