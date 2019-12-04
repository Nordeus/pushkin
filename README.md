# Unmaintained
This repository is no longer maintained.

# Pushkin
[![Build Status](https://travis-ci.org/Nordeus/pushkin.svg?branch=master)](https://travis-ci.org/Nordeus/pushkin)

## Introduction

Pushkin is a **free open source tool** for sending push notifications. It was developed with a focus on speed and enabling fast experimentation.
Pushkin was mainly built for supporting online mobile games, but can easily be extended to any type of application. It supports both Android and iOS platforms.

Pushkin is designed to be a responsive tool. You can design your systems around Pushkin so it reacts to your game server, database server, client or really any service that can send a HTTP POST request. It is also easily scalable, because you can run as many Pushkin instances as you want. One instance is capable of pushing 500 messages per second.

Pushkin has the MIT license.

---

## Use cases

To fit all use cases, Pushkin has 2 modes of operations:

1. **Push Notification mode** - You can issue a direct notification, meaning that you supply the user and the message. Pushkin will find the device id for the user and send the message. This is the simplest use case.

2. **Event mode** - You can send Pushkin an event, notifying it that something happened to a certain user. Pushkin will then decide whether it can send a notification based on that event or not. If yes, Pushkin will construct the message in the proper language for the user (localization is supported), find the device id of the user mobile device and send the notification.

These two use cases can be seen on the diagram below:

![highlevel](docs/img/Pushkin_Highlevel.png)
