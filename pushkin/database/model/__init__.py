# coding: utf-8

# auto generated code with sqlacodegen-1.1.6

'''
The MIT License (MIT)
Copyright (c) 2016 Nordeus LLC

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql


Base = declarative_base()
metadata = Base.metadata


class Device(Base):
    __tablename__ = 'device'
    __table_args__ = (
        UniqueConstraint('login_id', 'platform_id', 'device_token'),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('device_id_seq'::regclass)"))
    login_id = Column(ForeignKey('login.id', ondelete='CASCADE'), nullable=False, index=True)
    platform_id = Column(SmallInteger, nullable=False)
    device_token = Column(Text, nullable=False)
    device_token_new = Column(Text)
    application_version = Column(Integer)
    unregistered_ts = Column(DateTime)

    login = relationship('Login')


class Login(Base):
    __tablename__ = 'login'

    id = Column(BigInteger, primary_key=True)
    language_id = Column(SmallInteger)


class Message(Base):
    __tablename__ = 'message'

    id = Column(Integer, primary_key=True, server_default=text("nextval('message_id_seq'::regclass)"))
    name = Column(Text, nullable=False, unique=True)
    cooldown_ts = Column(BigInteger)
    trigger_event_id = Column(Integer)
    expiry_millis = Column(BigInteger)
    screen = Column(Text, nullable=False, server_default=text("''::text"))

class MessageBlacklist(Base):
    __tablename__ = 'message_blacklist'

    id = Column(Integer, primary_key=True, server_default=text("nextval('message_blacklist_id_seq'::regclass)"))
    login_id = Column(ForeignKey('login.id', ondelete='CASCADE'), nullable=False, index=True)
    blacklist = Column(postgresql.ARRAY(Integer))

class MessageLocalization(Base):
    __tablename__ = 'message_localization'
    __table_args__ = (
        UniqueConstraint('message_id', 'language_id'),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('message_localization_id_seq'::regclass)"))
    message_id = Column(ForeignKey('message.id', ondelete='CASCADE'), nullable=False)
    language_id = Column(SmallInteger, nullable=False)
    message_title = Column(Text, nullable=False)
    message_text = Column(Text, nullable=False)

    message = relationship('Message')


class UserMessageLastTimeSent(Base):
    __tablename__ = 'user_message_last_time_sent'
    __table_args__ = (
        UniqueConstraint('login_id', 'message_id'),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('user_message_last_time_sent_id_seq'::regclass)"))
    login_id = Column(ForeignKey('login.id', ondelete='CASCADE'), nullable=False)
    message_id = Column(ForeignKey('message.id', ondelete='CASCADE'), nullable=False)
    last_time_sent_ts_bigint = Column(BigInteger, nullable=False)

    login = relationship('Login')
    message = relationship('Message')


# Additional relationships
Login.devices = relationship("Device", order_by=Device.id, back_populates="login")
Message.localizations = relationship("MessageLocalization", order_by=MessageLocalization.id, back_populates="message")
