# coding: utf-8
from sqlalchemy import Column, DateTime, ForeignKey, Integer, SmallInteger, String, text
from sqlalchemy.orm import relationship
from . import Base


class ProtocolIrcChannel(Base):
    __tablename__ = 'protocol_irc_channels'

    id = Column(Integer, primary_key=True)
    network_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password = Column(String(255))
    user_id = Column(Integer, index=True)
    autojoin = Column(Integer, server_default=text("'1'"))


class ProtocolIrcNetwork(Base):
    __tablename__ = 'protocol_irc_networks'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(SmallInteger)
    server_password = Column(String(255))
    nick_id = Column(Integer, index=True)
    has_services = Column(Integer, server_default=text("'0'"))
    auth_method = Column(Integer)
    autojoin = Column(Integer, index=True, server_default=text("'1'"))
    user_id = Column(Integer, index=True)


class SystemUser(Base):
    __tablename__ = 'system_users'

    id = Column(ForeignKey('protocol_irc_channels.user_id'), ForeignKey('protocol_irc_networks.user_id'), primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    pass_hash = Column(String(60))
    pass_salt = Column(String(22))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    ip_address = Column(String(45))
    admin = Column(Integer, server_default=text("'0'"))

    # protocol_irc_channel = relationship('ProtocolIrcChannel', uselist=False)
